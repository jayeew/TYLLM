from collections.abc import Iterable


def judge_alerts(*, sales_records: Iterable[dict]) -> list[dict]:
    """库存预警规则占位。"""
    # TODO: 仅在业务规则、计算公式、字段口径被重新确认后实现预警判断。
    # 当前版本只允许读取 view_sales_daily_clean，不从销量字段推导任何预警等级或原因。
    _ = sales_records
    return []
