from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.calculations.alert_rule import judge_alert
from app.calculations.indicator_calculator import (
    calc_avg_daily_sales_7d,
    calc_coverage_days,
    calc_days_to_expiry,
)
from app.core.config import settings
from app.repositories.base_info_repo import BaseInfoRepo
from app.repositories.inventory_alert_repo import InventoryAlertRepo
from app.repositories.inventory_snapshot_repo import InventorySnapshotRepo
from app.repositories.pos_transaction_repo import PosTransactionRepo


TWO_DECIMAL = Decimal("0.01")


def format_decimal(value: Decimal) -> str:
    return str(value.quantize(TWO_DECIMAL, rounding=ROUND_HALF_UP))


class AlertService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.snapshot_repo = InventorySnapshotRepo(db)
        self.pos_repo = PosTransactionRepo(db)
        self.alert_repo = InventoryAlertRepo(db)
        self.base_info_repo = BaseInfoRepo(db)

    def scan_alerts(
        self,
        store_code: str | None = None,
        sku: Decimal | None = None,
    ) -> dict:
        now_ts = int(datetime.now().timestamp())
        snapshots = self.snapshot_repo.list_inventory_snapshots(store_code=store_code, sku=sku)
        store_names = self.base_info_repo.list_store_names(
            sorted({snapshot.store_code for snapshot in snapshots})
        )

        generated_count = 0

        try:
            self.alert_repo.clear_demo_alerts(store_code=store_code, sku=sku)

            for snapshot in snapshots:
                total_sales_qty = self.pos_repo.sum_sales_qty_last_7_days(
                    store_code=snapshot.store_code,
                    sku=snapshot.sku,
                    now_ts=now_ts,
                )
                # 平均日销量、预计销售时长、距批次过期天数
                avg_daily_sales = calc_avg_daily_sales_7d(total_sales_qty)
                coverage_days = calc_coverage_days(
                    snapshot.inventory_qty,
                    avg_daily_sales,
                    settings,
                )
                days_to_expiry = calc_days_to_expiry(snapshot.batch_expiry, now_ts)
                alert_result = judge_alert(
                    snapshot=snapshot,
                    avg_daily_sales=avg_daily_sales,
                    coverage_days=coverage_days,
                    days_to_expiry=days_to_expiry,
                )

                if not alert_result:
                    continue

                warning_store = store_names.get(snapshot.store_code, snapshot.store_code)
                warning_detail = (
                    f"门店：{snapshot.store_code}，SKU：{snapshot.sku}，商品：{snapshot.product_name}，"
                    f"库存数量：{format_decimal(snapshot.inventory_qty)}，"
                    f"近7天日均销量：{format_decimal(avg_daily_sales)}，"
                    f"库存覆盖天数：{format_decimal(coverage_days)}，"
                    f"预警原因：{alert_result['reason']}。"
                )
                self.alert_repo.insert_alert(
                    {
                        "store_code": snapshot.store_code,
                        "sku": snapshot.sku,
                        "product_name": snapshot.product_name,
                        "warnin g_category": alert_result["category"],
                        "warning_time": now_ts,
                        "warning_store": warning_store,
                        "warning_product_category": snapshot.product_category,
                        "warning_level": alert_result["level"],
                        "warning_detail": warning_detail,
                        "replenishment_suggestion": "建议触发补货预测",
                    }
                )
                generated_count += 1

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return {
            "success": True,
            "scanned_count": len(snapshots),
            "generated_count": generated_count,
            "message": "库存预警扫描完成",
        }
