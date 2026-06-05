from decimal import Decimal

from sqlalchemy import BigInteger, Identity, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.mappers.base import Base


class AdsInventoryForecast(Base):
    """补货预测结果表，存放建议补货日期、数量和预计到货时间。"""

    __tablename__ = "ads_inventory_forecast"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    store_code: Mapped[str] = mapped_column("门店编号", String, nullable=False)
    product_category: Mapped[str] = mapped_column("商品类别", Text, nullable=False)
    product_name: Mapped[str] = mapped_column("商品名称", Text, nullable=False)
    sku: Mapped[Decimal] = mapped_column("SKU货号", Numeric(20, 0), nullable=False)
    product_brand: Mapped[str | None] = mapped_column("商品品牌", Text, nullable=True)
    product_spec: Mapped[str | None] = mapped_column("商品规格", Text, nullable=True)
    suggested_replenishment_date: Mapped[int] = mapped_column(
        "建议补货日期", BigInteger, nullable=False
    )
    suggested_qty: Mapped[Decimal] = mapped_column("建议补货数量", Numeric(14, 2), nullable=False)
    main_supplier_name: Mapped[str | None] = mapped_column(
        "主供应商名称", Text, nullable=True
    )
    supplier_code: Mapped[Decimal | None] = mapped_column("供应商编号", Numeric, nullable=True)
    warehouse: Mapped[str | None] = mapped_column("仓库", Text, nullable=True)
    estimated_arrival_time: Mapped[int] = mapped_column("预计到货时间", BigInteger, nullable=False)
