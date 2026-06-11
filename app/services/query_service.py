from datetime import date

from app.config.database import ClickHouseClient
from app.repositories.inventory_alert_result_repo import InventoryAlertResultRepo
from app.repositories.replenishment_forecast_result_repo import (
    ReplenishmentForecastResultRepo,
)


class QueryService:
    """结果查询服务。"""

    def __init__(self, db: ClickHouseClient) -> None:
        self.alert_result_repo = InventoryAlertResultRepo(db)
        self.forecast_result_repo = ReplenishmentForecastResultRepo(db)

    def list_alerts(
        self,
        run_id: str | None = None,
        calc_date: date | None = None,
        org_code: str | None = None,
        sku: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """查询库存预警结果表。"""
        self.alert_result_repo.ensure_table()
        return self.alert_result_repo.list_records(
            run_id=run_id,
            calc_date=calc_date,
            org_code=org_code,
            product_code=sku,
            limit=limit,
        )

    def list_forecasts(
        self,
        run_id: str | None = None,
        calc_date: date | None = None,
        org_code: str | None = None,
        sku: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """查询补货预测结果表。"""
        self.forecast_result_repo.ensure_table()
        return self.forecast_result_repo.list_records(
            run_id=run_id,
            calc_date=calc_date,
            org_code=org_code,
            product_code=sku,
            limit=limit,
        )
