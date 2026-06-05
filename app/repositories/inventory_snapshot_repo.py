from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.mappers.fact_inventory_snapshot import FactInventorySnapshot


class InventorySnapshotRepo:
    """库存快照数据访问对象。"""

    def __init__(self, db: Session) -> None:
        """保存当前请求中的数据库会话。"""
        self.db = db

    def list_inventory_snapshots(
        self,
        store_code: Decimal | None = None,
        sku: Decimal | None = None,
    ) -> list[FactInventorySnapshot]:
        """查询库存快照，可按机构编码和商品编码过滤。"""
        stmt = select(FactInventorySnapshot).order_by(
            FactInventorySnapshot.store_code,
            FactInventorySnapshot.sku,
        )

        # store_code 在库存表中实际对应“机构编码”。
        if store_code:
            stmt = stmt.where(FactInventorySnapshot.store_code == store_code)
        if sku is not None:
            stmt = stmt.where(FactInventorySnapshot.sku == sku)

        return list(self.db.scalars(stmt).all())
