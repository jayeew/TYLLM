from datetime import date
from uuid import uuid4

from app.config.config import settings
from app.config.database import ClickHouseClient
from app.core.alert_rule import judge_alerts
from app.repositories.inventory_alert_result_repo import InventoryAlertResultRepo
from app.repositories.inventory_calculation_repo import InventoryCalculationRepo


class AlertService:
    """库存预警扫描业务服务。"""

    def __init__(
        self,
        db: ClickHouseClient,
    ) -> None:
        """初始化本服务依赖的仓储。"""
        self.calculation_repo = InventoryCalculationRepo(db)
        self.alert_result_repo = InventoryAlertResultRepo(db)

    def scan_alerts(
        self,
        org_code: str | None = None,
        sku: str | None = None,
        calc_date: date | None = None,
        limit: int | None = None,
    ) -> dict:
        """计算库存预警并写入追加快照。"""
        resolved_calc_date = calc_date or date.today()
        run_id = uuid4().hex
        input_records = self.calculation_repo.list_inputs(
            calc_date=resolved_calc_date,
            org_code=org_code,
            product_code=sku,
            limit=limit,
        )

        alert_results = judge_alerts(
            input_records=input_records,
            settings=settings,
            calc_date=resolved_calc_date,
            run_id=run_id,
        )
        self.alert_result_repo.ensure_table()
        written_count = self.alert_result_repo.insert_many(alert_results)

        return {
            "success": True,
            "run_id": run_id,
            "scanned_count": len(input_records),
            "generated_count": len(alert_results),
            "written_count": written_count,
            "message": "已完成库存预警计算，并写入 ads_inventory_alert_result 快照。",
        }
