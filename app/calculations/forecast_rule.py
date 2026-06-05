from decimal import Decimal, ROUND_CEILING


def nvl(value, default) -> Decimal:
    return value if value is not None else Decimal(str(default))


def ceil_to_min_order(raw_need: Decimal, min_order_qty: Decimal) -> Decimal:
    """
    将需求量向上取整到最小订货数量的倍数
    """
    if min_order_qty <= 0:
        min_order_qty = Decimal("1")
    multiplier = (raw_need / min_order_qty).to_integral_value(rounding=ROUND_CEILING)
    return multiplier * min_order_qty


def calculate_forecast(snapshot, avg_daily_sales: Decimal):
    purchase_cycle = nvl(snapshot.purchase_cycle_days, 0)
    delivery_cycle = nvl(snapshot.delivery_cycle_days, 0)
    delivery_days = nvl(snapshot.delivery_days, 0)
    # 进货周期+ 配送周期 + 送货天数 = 总提前期
    total_lead_days = purchase_cycle + delivery_cycle + delivery_days

    base_factor = nvl(snapshot.base_factor_k0, 1)
    correction_factor = nvl(snapshot.correction_factor, 1)
    # 销量修正因子 = 基础修正因子K0 * 修正因子
    factor = base_factor * correction_factor

    available_qty = nvl(snapshot.available_qty, 0)
    in_transit_qty = nvl(snapshot.in_transit_qty, 0)
    safety_buffer_days = nvl(snapshot.safety_buffer_days, 0)
    dynamic_safety_stock = nvl(snapshot.dynamic_safety_stock, 0)
    min_order_qty = nvl(snapshot.min_order_qty, 1)

    # 周期需求 = 平均日销量 * 销量修正因子 * 总提前期
    cycle_demand = avg_daily_sales * factor * total_lead_days
    # 安全库存需求 = max(动态安全库存, 平均日销量 * 安全缓冲天数)
    safety_stock_need = max(dynamic_safety_stock, avg_daily_sales * safety_buffer_days)
    # 需求量 = 周期需求 + 安全库存需求 - 可用库存 - 在途数量
    raw_need = cycle_demand + safety_stock_need - available_qty - in_transit_qty
    
    if raw_need <= 0:
        return None

    suggested_qty = ceil_to_min_order(raw_need, min_order_qty)

    return {
        "total_lead_days": total_lead_days,
        "cycle_demand": cycle_demand,
        "safety_stock_need": safety_stock_need,
        "raw_need": raw_need,
        "suggested_qty": suggested_qty,
    }
