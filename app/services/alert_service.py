from app.config.config import settings
from app.config.database import ClickHouseClient
from app.core.alert_rule import judge_alerts
from app.sources.clickhouse import ClickHouseSourceRepo


class AlertService:
    """库存预警扫描业务服务。"""

    def __init__(
        self,
        db: ClickHouseClient,
    ) -> None:
        """初始化本服务依赖的销售视图仓储。"""
        self.sales_repo = ClickHouseSourceRepo(settings, client=db)

    def scan_alerts(
        self,
        org_code: str | None = None,
        sku: str | None = None,
    ) -> dict:
        """读取 view_sales_daily_clean，并保留预警规则占位。"""
        sales_records = self.sales_repo.list_sales_daily_records(
            org_code=org_code,
            sku=sku,
        )

        alert_results = judge_alerts(sales_records=sales_records)
        # TODO: 预警结果写入方式待规则和结果表口径重新确认后再实现。

        return {
            "success": True,
            "scanned_count": len(sales_records),
            "generated_count": len(alert_results),
            "message": "已读取 view_sales_daily_clean；预警规则尚未实现，未生成预警结果。",
        }
