from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.inventory_alert_repo import InventoryAlertRepo
from app.repositories.inventory_forecast_repo import InventoryForecastRepo


class QueryService:
    def __init__(self, db: Session) -> None:
        self.alert_repo = InventoryAlertRepo(db)
        self.forecast_repo = InventoryForecastRepo(db)

    def list_alerts(
        self,
        store_code: str | None = None,
        sku: Decimal | None = None,
        warning_level: str | None = None,
        warning_category: str | None = None,
    ):
        return self.alert_repo.list_alerts(
            store_code=store_code,
            sku=sku,
            warning_level=warning_level,
            warning_category=warning_category,
        )

    def list_forecasts(
        self,
        store_code: str | None = None,
        sku: Decimal | None = None,
        product_category: str | None = None,
        warehouse: str | None = None,
    ):
        return self.forecast_repo.list_forecasts(
            store_code=store_code,
            sku=sku,
            product_category=product_category,
            warehouse=warehouse,
        )
