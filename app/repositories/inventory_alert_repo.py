from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.mappers.ads_inventory_alert import AdsInventoryAlert


class InventoryAlertRepo:
    """库存预警结果表数据访问对象。"""

    def __init__(self, db: Session) -> None:
        """保存当前请求中的数据库会话。"""
        self.db = db

    def insert_alert(self, alert_data: dict) -> AdsInventoryAlert:
        """写入一条库存预警结果。"""
        alert = AdsInventoryAlert(**alert_data)
        self.db.add(alert)
        # flush 后可以拿到数据库生成的主键，但事务仍由 service 统一提交。
        self.db.flush()
        return alert

    def list_alerts(
        self,
        store_code: str | None = None,
        sku: Decimal | None = None,
        warning_level: str | None = None,
        warning_category: str | None = None,
    ) -> list[AdsInventoryAlert]:
        """查询库存预警结果，支持常用筛选条件。"""
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
        """清理指定范围内的旧预警结果，便于 Demo 重复扫描。"""
        stmt = delete(AdsInventoryAlert)
        # 带条件清理可以避免按单店/SKU重跑时影响其他结果。
        if store_code:
            stmt = stmt.where(AdsInventoryAlert.store_code == store_code)
        if sku is not None:
            stmt = stmt.where(AdsInventoryAlert.sku == sku)
        self.db.execute(stmt)
