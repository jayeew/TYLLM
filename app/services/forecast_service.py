from app.config.config import settings
from app.config.database import ClickHouseClient
from app.core.forecast_rule import calculate_forecast
from app.sources.clickhouse import ClickHouseSourceRepo


class ForecastService:
    """补货需求预测业务服务。"""

    def __init__(
        self,
        db: ClickHouseClient,
    ) -> None:
        """初始化本服务依赖的销售视图仓储。"""
        self.sales_repo = ClickHouseSourceRepo(settings, client=db)

    def calculate_forecasts(
        self,
        org_code: str | None = None,
        sku: str | None = None,
    ) -> dict:
        """读取 view_sales_daily_clean，并保留补货预测规则占位。"""
        sales_records = self.sales_repo.list_sales_daily_records(
            org_code=org_code,
            sku=sku,
        )

        forecast_result = calculate_forecast(sales_records=sales_records)
        # TODO: 预测结果写入方式待规则和结果表口径重新确认后再实现。

        return {
            "success": True,
            "calculated_count": len(sales_records),
            "generated_count": 1 if forecast_result else 0,
            "skipped_count": 0,
            "message": "已读取 view_sales_daily_clean；补货预测规则尚未实现，未生成预测结果。",
        }
