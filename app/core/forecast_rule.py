from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING
from typing import Any

from app.core.indicator_calculator import (
    FORECAST_MISSING_FIELDS,
    ZERO,
    build_inventory_indicators,
    ceil_to_pack,
    first_positive,
    max_decimal,
    missing_fields_text,
    round_decimal,
    to_decimal,
)


def calculate_forecasts(
    *,
    input_records: list[dict[str, Any]],
    settings: Any,
    calc_date: date,
    run_id: str,
) -> list[dict[str, Any]]:
    """按补货周期需求、安全库存、有效库存和在途库存生成补货快照。"""
    return [
        build_forecast_result(
            record=record,
            settings=settings,
            calc_date=calc_date,
            run_id=run_id,
        )
        for record in input_records
    ]


def build_forecast_result(
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
    corrected_daily_demand = to_decimal(indicators["corrected_daily_demand"])
    effective_inventory_qty = to_decimal(indicators["effective_inventory_qty"])

    purchase_cycle_days = to_decimal(settings.replenish_default_purchase_cycle_days)
    replenish_cycle_demand = corrected_daily_demand * purchase_cycle_days
    safety_stock_qty = corrected_daily_demand * to_decimal(settings.replenish_safety_buffer_days)
    in_transit_qty = calculate_in_transit_qty(record)

    gap_qty = replenish_cycle_demand + safety_stock_qty - effective_inventory_qty - in_transit_qty
    raw_replenish_qty = max_decimal(gap_qty, ZERO)

    min_order_qty = first_positive(
        settings.replenish_default_min_order_qty,
        default=Decimal("1"),
    )
    pack_qty = first_positive(
        record.get("large_package_qty"),
        record.get("purchase_factor"),
        settings.replenish_default_pack_qty,
        default=Decimal("1"),
    )

    q_moq = ZERO if raw_replenish_qty == ZERO else max_decimal(raw_replenish_qty, min_order_qty)
    system_replenish_qty = ceil_to_pack(q_moq, pack_qty)

    # TODO: 当前缺少批次效期字段，临期库存停止补货逻辑预留，初版不触发停止补货。
    stop_replenishment_reason = None
    manual_replenish_qty = None
    final_replenish_qty = system_replenish_qty

    replenish_after_days = calculate_replenish_after_days(
        effective_inventory_qty=effective_inventory_qty,
        in_transit_qty=in_transit_qty,
        safety_stock_qty=safety_stock_qty,
        corrected_daily_demand=corrected_daily_demand,
        purchase_cycle_days=purchase_cycle_days,
    )
    suggested_replenish_date = calc_date + timedelta(days=ceil_days(replenish_after_days))
    expected_arrival_date = suggested_replenish_date + timedelta(days=ceil_days(purchase_cycle_days))

    return {
        "run_id": run_id,
        "calc_date": calc_date,
        "org_code": record["org_code"],
        "org_name": record.get("org_name"),
        "product_code": record["product_code"],
        "product_name": record.get("product_name"),
        "product_category_code": record.get("product_category_code"),
        "product_category_name": record.get("product_category_name"),
        "supplier_name": record.get("supplier_name"),
        "unit": record.get("unit"),
        "inventory_qty": indicators["inventory_qty"],
        "effective_inventory_qty": indicators["effective_inventory_qty"],
        "in_transit_qty": round_decimal(in_transit_qty, 3),
        "sales_avg_7": indicators["sales_avg_7"],
        "sales_avg_15": indicators["sales_avg_15"],
        "sales_avg_30": indicators["sales_avg_30"],
        "base_daily_sales": indicators["base_daily_sales"],
        "correction_factor": indicators["correction_factor"],
        "corrected_daily_demand": indicators["corrected_daily_demand"],
        "purchase_cycle_days": round_decimal(purchase_cycle_days, 2),
        "replenish_cycle_demand": round_decimal(replenish_cycle_demand, 3),
        "safety_stock_mode": "buffer_days",
        "safety_stock_qty": round_decimal(safety_stock_qty, 3),
        "gap_qty": round_decimal(gap_qty, 3),
        "raw_replenish_qty": round_decimal(raw_replenish_qty, 3),
        "min_order_qty": round_decimal(min_order_qty, 3),
        "pack_qty": round_decimal(pack_qty, 3),
        "system_replenish_qty": round_decimal(system_replenish_qty, 3),
        "manual_replenish_qty": manual_replenish_qty,
        "final_replenish_qty": round_decimal(final_replenish_qty, 3),
        "replenish_after_days": round_decimal(replenish_after_days, 2),
        "suggested_replenish_date": suggested_replenish_date,
        "expected_arrival_date": expected_arrival_date,
        "stop_replenishment_reason": stop_replenishment_reason,
        "missing_fields": missing_fields_text(FORECAST_MISSING_FIELDS),
    }


def calculate_in_transit_qty(record: dict[str, Any]) -> Decimal:
    """初版只计入未来增加门店可售库存的入库方向在途数量。"""
    # TODO: 销售在途、调拨在途、配退在途方向需业务确认，初版不计入。
    return (
        to_decimal(record.get("purchase_in_transit_qty"))
        + to_decimal(record.get("requisition_in_transit_qty"))
        + to_decimal(record.get("distribution_in_transit_qty"))
    )


def calculate_replenish_after_days(
    *,
    effective_inventory_qty: Decimal,
    in_transit_qty: Decimal,
    safety_stock_qty: Decimal,
    corrected_daily_demand: Decimal,
    purchase_cycle_days: Decimal,
) -> Decimal:
    if corrected_daily_demand <= ZERO:
        return ZERO
    buffer_days = (
        effective_inventory_qty
        + in_transit_qty
        - safety_stock_qty
    ) / corrected_daily_demand
    return max_decimal(buffer_days - purchase_cycle_days, ZERO)


def ceil_days(days: Decimal) -> int:
    if days <= ZERO:
        return 0
    return int(days.to_integral_value(rounding=ROUND_CEILING))
