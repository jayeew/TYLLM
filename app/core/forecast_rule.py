from decimal import Decimal, ROUND_CEILING


def ceil_package_count(raw_need_units: Decimal, replenishment_spec: Decimal) -> Decimal:
    """把原始需求量按补货规格向上取整为订货数量。"""
    if replenishment_spec <= 0:
        # 补货规格异常时按1个最小销售单位兜底，避免除零。
        replenishment_spec = Decimal("1")
    return (raw_need_units / replenishment_spec).to_integral_value(rounding=ROUND_CEILING)


def calculate_forecast(
    *,
    avg_daily_sales: Decimal,
    correction_factor: Decimal,
    purchase_cycle_days: Decimal | None,
    dynamic_safety_stock: Decimal,
    effective_inventory: Decimal,
    in_transit_qty: Decimal,
    replenishment_spec: Decimal,
    near_expiry_ratio: Decimal | None = None,
) -> dict | None:
    """计算建议补货数量；无法可靠计算时返回原因。"""
    # 需求文档要求临期库存占比≥50%时停止补货。
    if near_expiry_ratio is not None and near_expiry_ratio >= Decimal("0.5"):
        return {
            "can_calculate": False,
            "reason": "临期库存占比≥50%，按需求文档自动判定停止补货。",
        }

    # 近7天销量为0时需求文档要求优先清库存，不生成补货建议。
    if avg_daily_sales <= 0:
        return {
            "can_calculate": False,
            "reason": "近7天销量为0，按需求文档优先清库存，暂不生成补货数量。",
        }

    # 周期需求依赖进货周期；缺字段时不能凭空估算到货前需求。
    if purchase_cycle_days is None:
        return {
            "can_calculate": False,
            "reason": "缺少进货周期，无法计算周期需求量和预计到货时间。",
        }

    # 需求公式：周期需求量 = 近7天日均销量 * 修正因子 * 进货周期。
    cycle_demand = avg_daily_sales * correction_factor * purchase_cycle_days
    # 补货需求总量 = 周期需求 + 动态安全库存 - 有效库存 - 在途数量。
    raw_need_units = cycle_demand + dynamic_safety_stock - effective_inventory - in_transit_qty

    if raw_need_units <= 0:
        # 库存和在途已覆盖需求时，不生成预测记录。
        return None

    suggested_package_qty = ceil_package_count(raw_need_units, replenishment_spec)

    return {
        "can_calculate": True,
        "purchase_cycle_days": purchase_cycle_days,
        "cycle_demand": cycle_demand,
        "dynamic_safety_stock": dynamic_safety_stock,
        "raw_need_units": raw_need_units,
        "replenishment_spec": replenishment_spec,
        "suggested_qty": suggested_package_qty,
    }
