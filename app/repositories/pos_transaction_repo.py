from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.mappers.fact_pos_transaction import FactPosTransaction


class PosTransactionRepo:
    """POS 销售流水数据访问对象。"""

    def __init__(self, db: Session) -> None:
        """保存当前请求中的数据库会话。"""
        self.db = db

    def sum_sales_qty_last_7_days(
        self,
        store_code: str,
        sku: Decimal,
        now_ts: int,
    ) -> Decimal:
        """统计指定门店 SKU 最近7天的销售数量总和。"""
        seven_days_ago_ts = now_ts - 7 * 86400
        # 直接在数据库侧聚合，避免把明细全量拉回应用层。
        stmt = select(func.coalesce(func.sum(FactPosTransaction.sales_qty), 0)).where(
            FactPosTransaction.store_code == store_code,
            FactPosTransaction.sku == sku,
            FactPosTransaction.transaction_time >= seven_days_ago_ts,
        )
        result = self.db.execute(stmt).scalar_one()
        return Decimal(str(result))

    def list_daily_sales_qty(
        self,
        store_code: str,
        sku: Decimal,
        now_ts: int,
        days: int,
    ) -> list[Decimal]:
        """按自然日返回指定周期内每天的销量，缺失日期补0。"""
        start_ts = now_ts - days * 86400
        stmt = select(
            FactPosTransaction.transaction_time,
            FactPosTransaction.sales_qty,
        ).where(
            FactPosTransaction.store_code == store_code,
            FactPosTransaction.sku == sku,
            FactPosTransaction.transaction_time >= start_ts,
            FactPosTransaction.transaction_time <= now_ts,
        )
        rows = self.db.execute(stmt).all()

        daily_sales: dict = defaultdict(lambda: Decimal("0"))
        for transaction_time, sales_qty in rows:
            # POS 流水时间是秒级时间戳，先归并到日期再累计当天销量。
            sale_date = datetime.fromtimestamp(int(transaction_time)).date()
            daily_sales[sale_date] += Decimal(str(sales_qty))

        start_date = datetime.fromtimestamp(start_ts).date()
        # 固定返回 days 个元素，保证波动因子计算时序列长度稳定。
        return [
            daily_sales[start_date + timedelta(days=offset)]
            for offset in range(days)
        ]
