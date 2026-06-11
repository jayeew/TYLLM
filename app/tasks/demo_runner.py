from datetime import date

from app.config.database import ClickHouseClient
from app.services.alert_service import AlertService
from app.services.forecast_service import ForecastService


def run_demo(
    db: ClickHouseClient,
    org_code: str | None = None,
    sku: str | None = None,
    calc_date: date | None = None,
    limit: int | None = None,
) -> dict:
    """批量执行预警和补货预测流程，便于脚本或定时任务复用。"""
    alert_result = AlertService(db).scan_alerts(
        org_code=org_code,
        sku=sku,
        calc_date=calc_date,
        limit=limit,
    )
    forecast_result = ForecastService(db).calculate_forecasts(
        org_code=org_code,
        sku=sku,
        calc_date=calc_date,
        limit=limit,
    )
    return {
        "alerts": alert_result,
        "forecasts": forecast_result,
    }
