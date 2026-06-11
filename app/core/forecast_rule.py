from collections.abc import Iterable


def calculate_forecast(*, sales_records: Iterable[dict]) -> dict | None:
    """补货预测规则占位。"""
    # TODO: 仅在业务规则、计算公式、字段口径被重新确认后实现补货预测。
    # 当前版本只允许读取 view_sales_daily_clean，不从销量字段推导补货数量或到货时间。
    _ = sales_records
    return None
