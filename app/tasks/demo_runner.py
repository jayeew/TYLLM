from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.alert_service import AlertService
from app.services.forecast_service import ForecastService


def run_demo(
    db: Session,
    store_code: str | None = None,
    sku: Decimal | None = None,
) -> dict:
    alert_result = AlertService(db).scan_alerts(store_code=store_code, sku=sku)
    forecast_result = ForecastService(db).calculate_forecasts(store_code=store_code, sku=sku)
    return {
        "alerts": alert_result,
        "forecasts": forecast_result,
    }
