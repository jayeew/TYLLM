from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from statistics import pstdev


DEFAULT_SAFETY_BUFFER_DAYS = Decimal("3")
CORRECTION_FACTOR_MIN = Decimal("0.3")
CORRECTION_FACTOR_MAX = Decimal("3")
SAFETY_STOCK_FACTOR_MIN = Decimal("0.5")
SAFETY_STOCK_FACTOR_MAX = Decimal("3")


def nvl(value, default) -> Decimal:
    """把空值或普通数字统一转换成 Decimal，避免金额/数量计算精度漂移。"""
    if value is None:
        return Decimal(str(default))
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def clamp(value: Decimal, minimum: Decimal, maximum: Decimal) -> Decimal:
    """把数值限制在指定区间内。"""
    return max(minimum, min(maximum, value))


def normalize_code(value) -> str:
    """把数据库中的 Decimal 编码转成稳定的字符串编码。"""
    decimal_value = nvl(value, 0)
    # 编码字段通常是整数型 Decimal，转成 int 字符串可避免出现 10001.00。
    if decimal_value == decimal_value.to_integral_value():
        return str(int(decimal_value))
    return str(decimal_value.normalize())


def calc_avg_daily_sales_7d(total_sales_qty: Decimal) -> Decimal:
    """计算近7天日均销量。"""
    return total_sales_qty / Decimal("7")


def calc_effective_inventory(snapshot) -> Decimal:
    """计算当前有效库存，尽量扣除现有字段能识别的不可售数量。"""
    inventory_qty = nvl(snapshot.inventory_qty, 0)
    reserved_qty = nvl(getattr(snapshot, "sales_in_transit_qty", None), 0)
    return_qty = nvl(getattr(snapshot, "return_in_transit_qty", None), 0)

    # 实际库存快照没有“破损数量、过期数量、预订数量”字段。
    # 这里仅能把“销售在途数量”近似视为已占用库存，把“配退在途数量”视为不可售库存扣减。
    # 待源表补充破损/过期/预订明细后，应在这里继续扣减。
    return max(Decimal("0"), inventory_qty - reserved_qty - return_qty)


def calc_replenishment_in_transit(snapshot) -> Decimal:
    """计算补货在途数量。"""
    # 需求文档中的“在途库存”限定为已发起补货但尚未入库。
    # 当前表没有补货订单状态，只能使用采购/要货/调拨/配送在途字段近似；销售在途和配退在途不计入补货在途。
    fields = (
        "purchase_in_transit_qty",
        "requisition_in_transit_qty",
        "transfer_in_transit_qty",
        "distribution_in_transit_qty",
    )
    return sum((nvl(getattr(snapshot, field, None), 0) for field in fields), Decimal("0"))


def calc_purchase_cycle_days(snapshot) -> tuple[Decimal | None, list[str]]:
    """计算进货周期；字段不足时返回 None 和说明。"""
    delivery_cycle = getattr(snapshot, "delivery_cycle_days", None)
    delivery_days = getattr(snapshot, "delivery_days", None)
    purchase_cycle = getattr(snapshot, "purchase_cycle_days", None)

    # 优先按需求公式“进货周期=配送周期+送货天数”计算。
    if delivery_cycle is not None or delivery_days is not None:
        return nvl(delivery_cycle, 0) + nvl(delivery_days, 0), []

    # 兼容未来如果直接补充了进货周期字段的情况。
    if purchase_cycle is not None:
        return nvl(purchase_cycle, 0), []

    return None, [
        "无法计算进货周期：实际库存快照缺少配送周期、送货天数字段，且没有近6个月进货明细。"
    ]


def calc_correction_factor(
    snapshot,
    avg_daily_sales: Decimal,
    today: date | None = None,
) -> tuple[Decimal, list[str]]:
    """计算销量修正因子K，并返回计算过程中采用的说明。"""
    notes: list[str] = []

    # 需求文档指定近7天销量为0时默认 K=0.3，并优先清库存。
    if avg_daily_sales <= 0:
        notes.append("近7天销量为0，按需求文档默认修正因子K=0.3，并优先用于清库存判断。")
        return CORRECTION_FACTOR_MIN, notes

    # 当前没有商品生命周期起止日期，只能用商品状态近似判断新品/衰退期。
    status = (getattr(snapshot, "product_status", "") or "").strip()
    if "新品" in status:
        base_factor = Decimal("1.5")
        notes.append("商品状态为新品，基础修正因子K0取新品区间上限1.5。")
    elif any(keyword in status for keyword in ("停购", "停售", "停用", "淘汰", "下架")):
        base_factor = Decimal("0.6")
        notes.append("商品状态为停购/停售类，基础修正因子K0按衰退期取0.6。")
    else:
        base_factor = Decimal("1.0")

    # 周末因子可以直接从当前日期判断；法定节假日和旺季仍需要外部日历或配置。
    current_day = today or date.today()
    season_factor = Decimal("1.15") if current_day.weekday() >= 5 else Decimal("1.0")
    if current_day.weekday() >= 5:
        notes.append("当前日期为周末，季节/节假日因子F1按周末中间值1.15计算。")

    # 实际库表没有法定节假日、季节高峰、服务区客流或同比客流字段。
    # 因此F1暂不区分法定节假日/季节高峰，F2暂按客流平稳=1.0处理。
    traffic_factor = Decimal("1.0")
    # 需求文档默认权重：季节/节假日因子65%，客流趋势因子35%。
    weighted_factor = season_factor * Decimal("0.65") + traffic_factor * Decimal("0.35")
    correction_factor = base_factor * weighted_factor
    return clamp(correction_factor, CORRECTION_FACTOR_MIN, CORRECTION_FACTOR_MAX), notes


def calc_coverage_days(
    current_qty: Decimal,
    avg_daily_sales: Decimal,
    correction_factor: Decimal,
) -> Decimal | None:
    """计算预计销售时长T。"""
    # 需求公式：T = 当前库存量 / (近7天日均销量 * 修正因子K)。
    adjusted_daily_sales = avg_daily_sales * correction_factor
    if adjusted_daily_sales <= 0:
        return None
    return current_qty / adjusted_daily_sales


def calc_sales_volatility_factor(
    daily_sales_30d: list[Decimal],
    daily_sales_60d: list[Decimal],
) -> tuple[Decimal, list[str]]:
    """按近30天销量波动/近60天基础日均销量计算销量波动因子F1。"""
    notes: list[str] = []
    # 当前没有“无节假日”标记，基础日均销量暂用近60天全量日均销量近似。
    base_avg = (
        sum(daily_sales_60d, Decimal("0")) / Decimal(len(daily_sales_60d))
        if daily_sales_60d
        else Decimal("0")
    )

    if base_avg <= 0:
        notes.append("近60天基础日均销量为0，销量波动因子F1按最低区间0.8计算。")
        return Decimal("0.8"), notes

    # 标准差使用总体标准差，满足当前 Demo 的稳定性要求。
    stddev = Decimal(str(pstdev([float(value) for value in daily_sales_30d] or [0.0])))
    ratio = stddev / base_avg

    # 需求文档只给出区间，未给精确取值；这里取各区间中位值，后续可由模型复盘结果调整。
    if ratio <= Decimal("0.10"):
        factor = Decimal("0.9")
    elif ratio <= Decimal("0.30"):
        factor = Decimal("1.25")
    elif ratio <= Decimal("0.50"):
        factor = Decimal("1.75")
    else:
        factor = Decimal("2.25")

    return factor, notes


def calc_dynamic_safety_stock(
    base_safety_stock: Decimal,
    avg_daily_sales: Decimal,
    daily_sales_30d: list[Decimal],
    daily_sales_60d: list[Decimal],
) -> tuple[Decimal, list[str]]:
    """计算动态安全库存。"""
    notes: list[str] = []
    if base_safety_stock <= 0:
        base_safety_stock = avg_daily_sales * DEFAULT_SAFETY_BUFFER_DAYS
        notes.append("最小库存量为0，基础安全库存暂按近7天日均销量*默认安全缓冲3天估算。")

    if avg_daily_sales <= 0:
        notes.append("近7天销量为0，动态安全库存波动系数按需求文档默认F0=0.5。")
        return base_safety_stock * SAFETY_STOCK_FACTOR_MIN, notes

    # 销量波动因子使用近30/60天销量；进货周期波动因子暂按稳定处理。
    sales_factor, sales_notes = calc_sales_volatility_factor(daily_sales_30d, daily_sales_60d)
    notes.extend(sales_notes)

    # 当前数据库没有近180天多次进货周期记录，无法计算进货周期标准差σ2/平均进货周期L。
    # 进货周期波动因子F2暂按稳定=1.0处理，待补充采购/入库明细后替换。
    purchase_cycle_factor = Decimal("1.0")
    # 需求文档默认权重：销量波动70%，进货周期波动30%。
    weighted_factor = sales_factor * Decimal("0.7") + purchase_cycle_factor * Decimal("0.3")
    weighted_factor = clamp(
        weighted_factor,
        SAFETY_STOCK_FACTOR_MIN,
        SAFETY_STOCK_FACTOR_MAX,
    )
    return base_safety_stock * weighted_factor, notes


def parse_replenishment_spec(snapshot) -> tuple[Decimal, list[str]]:
    """解析补货规格，用于把原始需求量折算成箱/包等订货单位。"""
    notes: list[str] = []
    large_package_qty = getattr(snapshot, "large_package_qty", None)

    try:
        # 大包装数量如果是纯数字，优先作为补货规格。
        qty = nvl(large_package_qty, 0)
        if qty > 0:
            return qty, notes
    except (InvalidOperation, ValueError):
        pass

    # 大包装数量为空或不是纯数字时，尝试从“1*24”这类规格文本里解析。
    spec = (getattr(snapshot, "product_spec", None) or "").strip()
    normalized_spec = spec.replace("×", "*").replace("x", "*").replace("X", "*")
    if "*" in normalized_spec:
        numbers = re.findall(r"\d+(?:\.\d+)?", normalized_spec)
        if numbers:
            qty = Decimal("1")
            for number in numbers:
                qty *= Decimal(number)
            if qty > 0:
                notes.append("大包装数量为空，补货规格按商品规格中的乘数组合估算。")
                return qty, notes

    notes.append("无法从大包装数量/规格识别补货规格，暂按1个最小销售单位计算。")
    return Decimal("1"), notes
