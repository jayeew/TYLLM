from decimal import Decimal

from sqlalchemy import BigInteger, Identity, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.mappers.base import Base


class FactPosTransaction(Base):
    """POS 销售流水事实表，用于统计近7天、近30天等销售数据。"""

    __tablename__ = "fact_pos_transaction"
    # 同一订单下同一 SKU 只保留一条流水，避免重复统计销量。
    __table_args__ = (
        UniqueConstraint("订单编号", "SKU货号", name="ux_fact_pos_order_sku"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    order_no: Mapped[str] = mapped_column("订单编号", Text, nullable=False)
    store_code: Mapped[str] = mapped_column("门店编号", String, nullable=False)
    transaction_amount: Mapped[Decimal] = mapped_column(
        "交易金额", Numeric(14, 2), nullable=False
    )
    transaction_time: Mapped[int] = mapped_column("交易时间", BigInteger, nullable=False)
    sold_product: Mapped[str] = mapped_column("售卖商品", Text, nullable=False)
    sku: Mapped[Decimal] = mapped_column("SKU货号", Numeric(20, 0), nullable=False)
    product_name: Mapped[str] = mapped_column("商品名称", Text, nullable=False)
    sales_qty: Mapped[Decimal] = mapped_column("销售数量", Numeric(14, 2), nullable=False)
