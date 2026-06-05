from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.ads_inventory_forecast import AdsInventoryForecast


class InventoryForecastRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def insert_forecast(self, forecast_data: dict) -> AdsInventoryForecast:
        forecast = AdsInventoryForecast(**forecast_data)
        self.db.add(forecast)
        self.db.flush()
        return forecast

    def list_forecasts(
        self,
        store_code: str | None = None,
        sku: Decimal | None = None,
        product_category: str | None = None,
        warehouse: str | None = None,
    ) -> list[AdsInventoryForecast]:
        stmt = select(AdsInventoryForecast).order_by(
            AdsInventoryForecast.suggested_replenishment_date.desc(),
            AdsInventoryForecast.id.desc(),
        )

        if store_code:
            stmt = stmt.where(AdsInventoryForecast.store_code == store_code)
        if sku is not None:
            stmt = stmt.where(AdsInventoryForecast.sku == sku)
        if product_category:
            stmt = stmt.where(AdsInventoryForecast.product_category == product_category)
        if warehouse:
            stmt = stmt.where(AdsInventoryForecast.warehouse == warehouse)

        return list(self.db.scalars(stmt).all())

    def clear_demo_forecasts(
        self,
        store_code: str | None = None,
        sku: Decimal | None = None,
    ) -> None:
        stmt = delete(AdsInventoryForecast)
        if store_code:
            stmt = stmt.where(AdsInventoryForecast.store_code == store_code)
        if sku is not None:
            stmt = stmt.where(AdsInventoryForecast.sku == sku)
        self.db.execute(stmt)
