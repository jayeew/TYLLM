from decimal import Decimal


def judge_alert(snapshot, avg_daily_sales: Decimal, coverage_days: Decimal, days_to_expiry):
    if coverage_days < snapshot.purchase_cycle_days + snapshot.safety_buffer_days:
        return {
            "category": "补货预警",
            "level": "一级预警",
            "reason": "库存覆盖天数低于采购周期加安全缓冲天数",
        }
    
    if snapshot.available_qty <= avg_daily_sales * 2:
        return {
            "category": "补货预警",
            "level": "一级预警",
            "reason": "可用库存低于近7天日均销量的2倍",
        }

    if snapshot.purchase_cycle_days * 0.5 <= coverage_days and coverage_days < snapshot.purchase_cycle_days:
        return {
            "category": "补货预警",
            "level": "二级预警",
            "reason": "库存覆盖天数接近采购周期加安全缓冲天数",
        }
    
    if snapshot.available_qty <= avg_daily_sales * 5:
        return {
            "category": "补货预警",
            "level": "二级预警",
            "reason": "可用库存低于近7天日均销量的5倍",
        }

    if snapshot.purchase_cycle_days < coverage_days and coverage_days <= snapshot.purchase_cyclr_days + snapshot.safety_buffer_days:
        return {
            "category": "补货预警",
            "level": "三级预警",
            "reason": "库存覆盖天数略高于采购周期加安全缓冲天数",
        }
    
    if snapshot.available_qty <= avg_daily_sales * 8:
        return {
            "category": "补货预警",
            "level": "三级预警",
            "reason": "可用库存低于近7天日均销量的8倍",
        }
    
    

    if days_to_expiry is not None and days_to_expiry < 0:
        return {
            "category": "过期预警",
            "level": "三级预警",
            "reason": "商品批次已过期",
        }

    safety_buffer_days = snapshot.safety_buffer_days or Decimal("0")
    if days_to_expiry is not None and days_to_expiry <= safety_buffer_days:
        return {
            "category": "临期预警",
            "level": "二级预警",
            "reason": "商品接近批次效期",
        }

    safety_threshold = snapshot.safety_threshold or Decimal("0")
    if snapshot.available_qty <= safety_threshold:
        return {
            "category": "安全库存预警",
            "level": "一级预警",
            "reason": "可用库存低于安全阈值",
        }

    return None
