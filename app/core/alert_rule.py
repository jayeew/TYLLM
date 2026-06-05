from decimal import Decimal


LEVEL_ORDER = {
    # 数字越小表示预警越严重，用于多条件命中时选最高等级。
    "一级预警": 1,
    "二级预警": 2,
    "三级预警": 3,
}


def _strongest_warning(warnings: list[dict]) -> dict | None:
    """从多个候选预警中挑出最高等级的一条。"""
    if not warnings:
        return None
    return sorted(warnings, key=lambda item: LEVEL_ORDER[item["level"]])[0]


def judge_alerts(
    *,
    avg_daily_sales: Decimal,
    coverage_days: Decimal | None,
    effective_inventory: Decimal,
    purchase_cycle_days: Decimal | None,
    safety_buffer_days: Decimal,
    near_expiry_ratio: Decimal | None = None,
    expired_qty: Decimal | None = None,
) -> list[dict]:
    """根据需求文档规则生成库存预警列表。"""
    alerts: list[dict] = []
    replenishment_warnings: list[dict] = []

    # 第一组补货规则：根据预计销售时长T与进货周期、安全缓冲天数判断。
    if purchase_cycle_days is not None and coverage_days is not None:
        half_cycle = purchase_cycle_days * Decimal("0.5")
        if coverage_days < half_cycle:
            replenishment_warnings.append(
                {
                    "category": "补货预警",
                    "level": "一级预警",
                    "reason": "预计销售时长T低于进货周期50%，需立即补货。",
                }
            )
        elif half_cycle <= coverage_days <= purchase_cycle_days:
            replenishment_warnings.append(
                {
                    "category": "补货预警",
                    "level": "二级预警",
                    "reason": "预计销售时长T介于进货周期50%和进货周期之间，需补货。",
                }
            )
        elif purchase_cycle_days < coverage_days <= purchase_cycle_days + safety_buffer_days:
            replenishment_warnings.append(
                {
                    "category": "补货预警",
                    "level": "三级预警",
                    "reason": "预计销售时长T介于进货周期和进货周期+安全缓冲天数之间。",
                }
            )

    # 第二组补货规则：根据有效库存与近7天日均销量倍数判断。
    if avg_daily_sales > 0:
        if effective_inventory <= avg_daily_sales * Decimal("2"):
            replenishment_warnings.append(
                {
                    "category": "补货预警",
                    "level": "一级预警",
                    "reason": "有效库存不高于近7天日均销量的2倍。",
                }
            )
        elif effective_inventory <= avg_daily_sales * Decimal("5"):
            replenishment_warnings.append(
                {
                    "category": "补货预警",
                    "level": "二级预警",
                    "reason": "有效库存不高于近7天日均销量的5倍。",
                }
            )
        elif effective_inventory <= avg_daily_sales * Decimal("8"):
            replenishment_warnings.append(
                {
                    "category": "补货预警",
                    "level": "三级预警",
                    "reason": "有效库存不高于近7天日均销量的8倍。",
                }
            )

    # 同一个商品可能同时命中T规则和库存倍数规则，只保留最高等级，避免重复补货预警。
    strongest_replenishment = _strongest_warning(replenishment_warnings)
    if strongest_replenishment:
        same_level_reasons = [
            item["reason"]
            for item in replenishment_warnings
            if item["level"] == strongest_replenishment["level"]
        ]
        strongest_replenishment["reason"] = "；".join(same_level_reasons)
        alerts.append(strongest_replenishment)

    # 实际库存快照没有批次效期、保质期、临期批次数量、过期批次数量。
    # 因此临期占比与过期库存规则只有在调用方补充 near_expiry_ratio/expired_qty 后才会生效。
    if near_expiry_ratio is not None:
        # 临期占比规则来自需求文档：≥50%一级，30%-50%二级。
        if near_expiry_ratio >= Decimal("0.5"):
            alerts.append(
                {
                    "category": "临期商品预警",
                    "level": "一级预警",
                    "reason": "保质期≤20天商品库存占比不低于50%。",
                }
            )
        elif Decimal("0.3") <= near_expiry_ratio < Decimal("0.5"):
            alerts.append(
                {
                    "category": "临期商品预警",
                    "level": "二级预警",
                    "reason": "保质期≤20天商品库存占比介于30%和50%之间。",
                }
            )

    # 过期商品只要存在即按二级预警提醒清退。
    if expired_qty is not None and expired_qty > 0:
        alerts.append(
            {
                "category": "过期商品预警",
                "level": "二级预警",
                "reason": "当前库存中存在过期商品，需及时清退。",
            }
        )

    return alerts
