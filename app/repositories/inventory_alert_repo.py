from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.ads_inventory_alert import AdsInventoryAlert


class InventoryAlertRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def insert_alert(self, alert_data: dict) -> AdsInventoryAlert:
        alert = AdsInventoryAlert(**alert_data)
        self.db.add(alert)
        self.db.flush()
        return alert

    def list_alerts(
        self,
        store_code: str | None = None,
        sku: Decimal | None = None,
        warning_level: str | None = None,
        warning_category: str | None = None,
    ) -> list[AdsInventoryAlert]:
        stmt = select(AdsInventoryAlert).order_by(
            AdsInventoryAlert.warning_time.desc(),
            AdsInventoryAlert.id.desc(),
        )

        if store_code:
            stmt = stmt.where(AdsInventoryAlert.store_code == store_code)
        if sku is not None:
            stmt = stmt.where(AdsInventoryAlert.sku == sku)
        if warning_level:
            stmt = stmt.where(AdsInventoryAlert.warning_level == warning_level)
        if warning_category:
            stmt = stmt.where(AdsInventoryAlert.warning_category == warning_category)

        return list(self.db.scalars(stmt).all())

    def clear_demo_alerts(
        self,
        store_code: str | None = None,
        sku: Decimal | None = None,
    ) -> None:
        stmt = delete(AdsInventoryAlert)
        if store_code:
            stmt = stmt.where(AdsInventoryAlert.store_code == store_code)
        if sku is not None:
            stmt = stmt.where(AdsInventoryAlert.sku == sku)
        self.db.execute(stmt)
