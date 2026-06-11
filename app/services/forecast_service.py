from datetime import date
from uuid import uuid4

from app.config.config import settings
from app.config.database import ClickHouseClient
from app.core.forecast_rule import calculate_forecasts
from app.sources.clickhouse import ClickHouseSourceRepo


class ForecastService:
    """补货需求预测业务服务。"""

    def __init__(
        self,
        db: ClickHouseClient,
    ) -> None:
        """初始化本服务依赖的 ClickHouse 源表仓储。"""
        self.source_repo = ClickHouseSourceRepo(settings, client=db)

    def calculate_forecasts(
        self,
        org_code: str | None = None,
        sku: str | None = None,
        calc_date: date | None = None,
        limit: int | None = None,
    ) -> dict:
        """计算补货预测并写入追加快照。"""
        resolved_calc_date = calc_date or date.today()
        run_id = uuid4().hex
        input_records = self.source_repo.list_inventory_calculation_inputs(
            calc_date=resolved_calc_date,
            org_code=org_code,
            product_code=sku,
            limit=limit,
        )

        forecast_results = calculate_forecasts(
            input_records=input_records,
            settings=settings,
            calc_date=resolved_calc_date,
            run_id=run_id,
        )
        self.source_repo.ensure_result_tables()
        written_count = self.source_repo.insert_forecast_results(forecast_results)

        return {
            "success": True,
            "run_id": run_id,
            "calculated_count": len(input_records),
            "generated_count": len(forecast_results),
            "written_count": written_count,
            "skipped_count": 0,
            "message": "已完成补货预测计算，并写入 ads_replenishment_forecast_result 快照。",
        }
