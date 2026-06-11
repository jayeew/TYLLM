from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from app.core.indicator_calculator import (
    ALERT_MISSING_FIELDS,
    ZERO,
    build_inventory_indicators,
    missing_fields_text,
    round_decimal,
    to_decimal,
)


def judge_alerts(
    *,
    input_records: list[dict[str, Any]],
    settings: Any,
    calc_date: date,
    run_id: str,
) -> list[dict[str, Any]]:
    """按库存覆盖天数和安全库存缺口生成预警结果快照。"""
    return [
        build_alert_result(
            record=record,
            settings=settings,
            calc_date=calc_date,
            run_id=run_id,
        )
        for record in input_records
    ]


def build_alert_result(
    *,
    record: dict[str, Any],
    settings: Any,
    calc_date: date,
    run_id: str,
) -> dict[str, Any]:
    indicators = build_inventory_indicators(
        record=record,
        settings=settings,
        calc_date=calc_date,
    )

    safety_stock_qty = choose_safety_stock_qty(record=record, settings=settings)
    effective_inventory_qty = to_decimal(indicators["effective_inventory_qty"])
    safety_stock_gap = safety_stock_qty - effective_inventory_qty

    # TODO: 当前缺少批次效期字段，临期库存、过期库存初版只能写 0。
    expired_stock_qty = ZERO
    expiring_stock_qty = ZERO
    expiring_stock_ratio = ZERO

    level, level_name, alert_type, alert_status, reason = judge_alert_level(
        warning_risk_days=indicators["warning_risk_days"],
        safety_stock_gap=safety_stock_gap,
        expired_stock_qty=expired_stock_qty,
        expiring_stock_ratio=expiring_stock_ratio,
        settings=settings,
    )

    return {
        "run_id": run_id,
        "calc_date": calc_date,
        "org_code": record["org_code"],
        "org_name": record.get("org_name"),
        "product_code": record["product_code"],
        "product_name": record.get("product_name"),
        "product_category_code": record.get("product_category_code"),
        "product_category_name": record.get("product_category_name"),
        "unit": record.get("unit"),
        **indicators,
        "safety_stock_qty": round_decimal(safety_stock_qty, 3),
        "safety_stock_gap": round_decimal(safety_stock_gap, 3),
        "expired_stock_qty": round_decimal(expired_stock_qty, 3),
        "expiring_stock_qty": round_decimal(expiring_stock_qty, 3),
        "expiring_stock_ratio": round_decimal(expiring_stock_ratio, 4),
        "alert_status": alert_status,
        "alert_type": alert_type,
        "warning_level": level,
        "warning_level_name": level_name,
        "reason": reason,
        "missing_fields": missing_fields_text(ALERT_MISSING_FIELDS),
    }


def choose_safety_stock_qty(*, record: dict[str, Any], settings: Any) -> Decimal:
    min_inventory_qty = to_decimal(record.get("min_inventory_qty"))
    if min_inventory_qty > ZERO:
        return min_inventory_qty
    return to_decimal(settings.alert_default_safety_stock_qty)


def judge_alert_level(
    *,
    warning_risk_days: Decimal | None,
    safety_stock_gap: Decimal,
    expired_stock_qty: Decimal,
    expiring_stock_ratio: Decimal,
    settings: Any,
) -> tuple[int | None, str | None, str, str, str]:
    if expired_stock_qty > ZERO:
        return None, None, "过期提示", "warning", "存在过期库存，需优先处理。"

    if expiring_stock_ratio >= to_decimal(settings.alert_expiring_stock_ratio_limit):
        return None, None, "临期预警", "warning", "临期库存占比达到停止补货阈值。"

    if safety_stock_gap > ZERO:
        return (
            3,
            "三级预警",
            "库存预警",
            "warning",
            f"有效库存低于安全库存，缺口 {round_decimal(safety_stock_gap, 3)}。",
        )

    if warning_risk_days is None:
        return None, None, "库存充足", "sufficient", "无销量覆盖天数，初版未触发风险。"

    level3 = to_decimal(settings.alert_level3_coverage_days)
    level2 = to_decimal(settings.alert_level2_coverage_days)
    level1 = to_decimal(settings.alert_level1_coverage_days)

    if warning_risk_days <= level3:
        return 3, "三级预警", "库存预警", "warning", build_coverage_reason(warning_risk_days, 3)
    if warning_risk_days <= level2:
        return 2, "二级预警", "库存预警", "warning", build_coverage_reason(warning_risk_days, 2)
    if warning_risk_days <= level1:
        return 1, "一级预警", "库存预警", "warning", build_coverage_reason(warning_risk_days, 1)

    return None, None, "库存充足", "sufficient", "库存覆盖天数高于预警阈值。"


def build_coverage_reason(warning_risk_days: Decimal, level: int) -> str:
    return f"库存风险天数 {round_decimal(warning_risk_days, 2)} 触发{level}级预警。"
