from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.fact_pos_transaction import FactPosTransaction


class PosTransactionRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def sum_sales_qty_last_7_days(
        self,
        store_code: str,
        sku: Decimal,
        now_ts: int,
    ) -> Decimal:
        seven_days_ago_ts = now_ts - 7 * 86400
        stmt = select(func.coalesce(func.sum(FactPosTransaction.sales_qty), 0)).where(
            FactPosTransaction.store_code == store_code,
            FactPosTransaction.sku == sku,
            FactPosTransaction.transaction_time >= seven_days_ago_ts,
        )
        result = self.db.execute(stmt).scalar_one()
        return Decimal(str(result))
