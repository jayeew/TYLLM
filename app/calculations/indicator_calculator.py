from decimal import Decimal


def calc_avg_daily_sales_7d(total_sales_qty: Decimal) -> Decimal:
    return total_sales_qty / Decimal("7")


def calc_coverage_days(available_qty: Decimal, avg_daily_sales: Decimal, settings) -> Decimal:
    if avg_daily_sales > 0:
        # factor = seetings.
        return available_qty / (avg_daily_sales * settings.alert_correction_factor)
    if available_qty > 0:
        return Decimal("999")
    return Decimal("0")


def calc_days_to_expiry(batch_expiry_ts: int | None, now_ts: int) -> Decimal | None:
    if batch_expiry_ts is None:
        return None
    return Decimal(batch_expiry_ts - now_ts) / Decimal("86400")
