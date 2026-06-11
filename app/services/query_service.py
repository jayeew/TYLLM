from datetime import date

from app.config.config import settings
from app.config.database import ClickHouseClient
from app.sources.clickhouse import ClickHouseSourceRepo


class QueryService:
    """结果查询服务。"""

    def __init__(self, db: ClickHouseClient) -> None:
        self.source_repo = ClickHouseSourceRepo(settings, client=db)

    def list_alerts(
        self,
        run_id: str | None = None,
        calc_date: date | None = None,
        org_code: str | None = None,
        sku: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """查询库存预警结果表。"""
        self.source_repo.ensure_result_tables()
        return self.source_repo.list_alert_results(
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
        self.source_repo.ensure_result_tables()
        return self.source_repo.list_forecast_results(
            run_id=run_id,
            calc_date=calc_date,
            org_code=org_code,
            product_code=sku,
            limit=limit,
        )
