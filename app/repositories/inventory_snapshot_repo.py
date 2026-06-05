from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fact_inventory_snapshot import FactInventorySnapshot


class InventorySnapshotRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_inventory_snapshots(
        self,
        store_code: str | None = None,
        sku: Decimal | None = None,
    ) -> list[FactInventorySnapshot]:
        stmt = select(FactInventorySnapshot).order_by(
            FactInventorySnapshot.store_code,
            FactInventorySnapshot.sku,
        )

        if store_code:
            stmt = stmt.where(FactInventorySnapshot.store_code == store_code)
        if sku is not None:
            stmt = stmt.where(FactInventorySnapshot.sku == sku)

        return list(self.db.scalars(stmt).all())
