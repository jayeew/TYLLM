from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.mappers.ads_inventory_forecast import AdsInventoryForecast


class InventoryForecastRepo:
    """补货预测结果表数据访问对象。"""

    def __init__(self, db: Session) -> None:
        """保存当前请求中的数据库会话。"""
        self.db = db

    def insert_forecast(self, forecast_data: dict) -> AdsInventoryForecast:
        """写入一条补货预测结果。"""
        forecast = AdsInventoryForecast(**forecast_data)
        self.db.add(forecast)
        # flush 后可以拿到数据库生成的主键，但事务仍由 service 统一提交。
        self.db.flush()
        return forecast

    def list_forecasts(
        self,
        store_code: str | None = None,
        sku: Decimal | None = None,
        product_category: str | None = None,
        warehouse: str | None = None,
    ) -> list[AdsInventoryForecast]:
        """查询补货预测结果，支持门店、SKU、品类和仓库筛选。"""
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
        """清理指定范围内的旧预测结果，便于 Demo 重复计算。"""
        stmt = delete(AdsInventoryForecast)
        # 带条件清理可以避免按单店/SKU重跑时影响其他结果。
        if store_code:
            stmt = stmt.where(AdsInventoryForecast.store_code == store_code)
        if sku is not None:
            stmt = stmt.where(AdsInventoryForecast.sku == sku)
        self.db.execute(stmt)
