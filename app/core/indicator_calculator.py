from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_CEILING
from typing import Any


ALERT_MISSING_FIELDS = (
    "damaged_qty",
    "expired_batch_stock_qty",
    "reserved_qty",
    "expiring_batch_stock_qty",
    "batch_expiry_date",
    "real_customer_flow",
)

FORECAST_MISSING_FIELDS = (
    "expiring_batch_stock_qty",
    "batch_expiry_date",
    "purchase_order_history",
    "delivery_cycle_days",
    "sales_volatility_factor",
    "purchase_cycle_volatility_factor",
    "real_customer_flow",
)


ZERO = Decimal("0")
ONE = Decimal("1")


def build_inventory_indicators(
    *,
    record: dict[str, Any],
    settings: Any,
    calc_date: date,
) -> dict[str, Any]:
    """基于三张可用表计算预警和补货共享指标。"""
    sales_avg_7 = to_decimal(record.get("sales_avg_7"))
    sales_avg_15 = to_decimal(record.get("sales_avg_15"))
    sales_avg_30 = to_decimal(record.get("sales_avg_30"))
    base_daily_sales = choose_base_daily_sales(
        sales_avg_7=sales_avg_7,
        sales_avg_15=sales_avg_15,
        sales_avg_30=sales_avg_30,
    )

    inventory_qty = to_decimal(record.get("inventory_qty"))
    # TODO: 当前缺少破损、过期、预订、锁定库存字段；初版把库存数量视为可用库存和有效库存。
    available_inventory_qty = inventory_qty
    effective_inventory_qty = inventory_qty

    correction_factor = build_correction_factor(settings=settings, calc_date=calc_date)
    corrected_daily_demand = (
        base_daily_sales * correction_factor
        if base_daily_sales > ZERO
        else ONE
    )

    coverage_days = safe_divide(available_inventory_qty, base_daily_sales)
    estimated_sale_days = safe_divide(inventory_qty, corrected_daily_demand)
    risk_candidates = [
        value
        for value in (coverage_days, estimated_sale_days)
        if value is not None
    ]

    return {
        "inventory_qty": round_decimal(inventory_qty, 3),
        "available_inventory_qty": round_decimal(available_inventory_qty, 3),
        "effective_inventory_qty": round_decimal(effective_inventory_qty, 3),
        "sales_avg_7": round_decimal(sales_avg_7, 4),
        "sales_avg_15": round_decimal(sales_avg_15, 4),
        "sales_avg_30": round_decimal(sales_avg_30, 4),
        "base_daily_sales": round_decimal(base_daily_sales, 4),
        "correction_factor": round_decimal(correction_factor, 4),
        "corrected_daily_demand": round_decimal(corrected_daily_demand, 4),
        "coverage_days": round_optional_decimal(coverage_days, 2),
        "estimated_sale_days": round_optional_decimal(estimated_sale_days, 2),
        "warning_risk_days": round_optional_decimal(
            min(risk_candidates) if risk_candidates else None,
            2,
        ),
    }


def choose_base_daily_sales(
    *,
    sales_avg_7: Decimal,
    sales_avg_15: Decimal,
    sales_avg_30: Decimal,
) -> Decimal:
    """按 7 天、15 天、30 天顺序回退选择基础日销量。"""
    if sales_avg_7 > ZERO:
        return sales_avg_7
    if sales_avg_15 > ZERO:
        return sales_avg_15
    if sales_avg_30 > ZERO:
        return sales_avg_30
    return ZERO


def build_correction_factor(*, settings: Any, calc_date: date) -> Decimal:
    """初版修正因子：成熟期 K0 × 工作日/周末 F_date × 客流平稳 F_flow。"""
    # TODO: 后续接入新品生命周期、法定节假日、旺季配置和真实客流趋势。
    lifecycle_factor = to_decimal(settings.alert_factor_k0_phase2)
    date_factor = (
        to_decimal(settings.alert_factor_k1_weekend)
        if calc_date.weekday() >= 5
        else to_decimal(settings.alert_factor_k1_workday)
    )
    flow_factor = to_decimal(settings.alert_factor_k2_stable)
    return lifecycle_factor * date_factor * flow_factor


def safe_divide(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    """除数为 0 时返回 None，避免库存覆盖天数除零。"""
    if denominator == ZERO:
        return None
    return numerator / denominator


def ceil_to_pack(value: Decimal, pack_qty: Decimal) -> Decimal:
    """按箱规/包装规格向上取整。"""
    if value <= ZERO:
        return ZERO
    if pack_qty <= ZERO:
        return value.to_integral_value(rounding=ROUND_CEILING)
    multiplier = (value / pack_qty).to_integral_value(rounding=ROUND_CEILING)
    return multiplier * pack_qty


def first_positive(*values: Any, default: Decimal) -> Decimal:
    """返回第一个大于 0 的 Decimal 值。"""
    for value in values:
        decimal_value = to_decimal(value)
        if decimal_value > ZERO:
            return decimal_value
    return default


def max_decimal(*values: Decimal) -> Decimal:
    return max(values) if values else ZERO


def to_decimal(value: Any, default: Decimal = ZERO) -> Decimal:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def round_decimal(value: Decimal, places: int) -> Decimal:
    quantizer = Decimal("1").scaleb(-places)
    return value.quantize(quantizer)


def round_optional_decimal(value: Decimal | None, places: int) -> Decimal | None:
    if value is None:
        return None
    return round_decimal(value, places)


def missing_fields_text(fields: tuple[str, ...]) -> str:
    return ",".join(fields)


def build_sales_indicators(*, sales_records: Any) -> dict:
    """兼容旧占位入口；新规则使用 build_inventory_indicators。"""
    _ = sales_records
    return {}
