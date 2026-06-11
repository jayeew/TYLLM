from collections.abc import Iterable


def build_sales_indicators(*, sales_records: Iterable[dict]) -> dict:
    """指标计算占位。"""
    # TODO: 仅在指标定义、字段口径和计算公式被重新确认后实现。
    # 当前版本不计算日均销量、修正因子、安全库存、有效库存、在途数量等任何指标。
    _ = sales_records
    return {}
