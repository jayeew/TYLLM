from datetime import datetime, time, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.calculations.forecast_rule import calculate_forecast
from app.calculations.indicator_calculator import calc_avg_daily_sales_7d
from app.repositories.inventory_forecast_repo import InventoryForecastRepo
from app.repositories.inventory_snapshot_repo import InventorySnapshotRepo
from app.repositories.pos_transaction_repo import PosTransactionRepo


class ForecastService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.snapshot_repo = InventorySnapshotRepo(db)
        self.pos_repo = PosTransactionRepo(db)
        self.forecast_repo = InventoryForecastRepo(db)

    def calculate_forecasts(
        self,
        store_code: str | None = None,
        sku: Decimal | None = None,
    ) -> dict:
        now = datetime.now().astimezone()
        now_ts = int(now.timestamp())
        day_start = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)
        suggested_replenishment_date = int(day_start.timestamp())
        snapshots = self.snapshot_repo.list_inventory_snapshots(store_code=store_code, sku=sku)

        generated_count = 0

        try:
            self.forecast_repo.clear_demo_forecasts(store_code=store_code, sku=sku)

            for snapshot in snapshots:
                total_sales_qty = self.pos_repo.sum_sales_qty_last_7_days(
                    store_code=snapshot.store_code,
                    sku=snapshot.sku,
                    now_ts=now_ts,
                )
                avg_daily_sales = calc_avg_daily_sales_7d(total_sales_qty)
                forecast_result = calculate_forecast(snapshot=snapshot, avg_daily_sales=avg_daily_sales)

                if not forecast_result:
                    continue

                estimated_arrival_time = int(
                    (
                        day_start
                        + timedelta(days=float(forecast_result["total_lead_days"]))
                    ).timestamp()
                )
                self.forecast_repo.insert_forecast(
                    {
                        "store_code": snapshot.store_code,
                        "product_category": snapshot.product_category,
                        "product_name": snapshot.product_name,
                        "sku": snapshot.sku,
                        "product_brand": snapshot.product_brand,
                        "product_spec": snapshot.product_spec,
                        "suggested_replenishment_date": suggested_replenishment_date,
                        "suggested_qty": forecast_result["suggested_qty"],
                        "main_supplier_name": snapshot.main_supplier_name,
                        "supplier_code": snapshot.supplier_code,
                        "warehouse": snapshot.warehouse,
                        "estimated_arrival_time": estimated_arrival_time,
                    }
                )
                generated_count += 1

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return {
            "success": True,
            "calculated_count": len(snapshots),
            "generated_count": generated_count,
            "message": "补货需求预测完成",
        }
