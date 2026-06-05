from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, Identity, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.mappers.base import Base


class FactInventorySnapshot(Base):
    """商品库存快照事实表，对应实际库存导入字段。"""

    __tablename__ = "fact_inventory_snapshot"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    # 实际库存表没有“门店编号/SKU货号”，这里分别映射为机构编码/商品编码。
    store_code: Mapped[Decimal] = mapped_column("机构编码", Numeric(14, 2), nullable=False)
    store_name: Mapped[str] = mapped_column("机构名称", Text, nullable=False)
    sku: Mapped[Decimal] = mapped_column("商品编码", Numeric(10, 0), nullable=False)
    international_barcode: Mapped[Decimal] = mapped_column(
        "国际条码", Numeric(13, 0), nullable=False
    )
    product_category: Mapped[Decimal] = mapped_column(
        "商品类别", Numeric(6, 0), nullable=False
    )
    product_category_name: Mapped[str] = mapped_column("商品类别名称", Text, nullable=False)
    supplier: Mapped[str] = mapped_column("供应商", Text, nullable=False)
    unit: Mapped[str] = mapped_column("单位", Text, nullable=False)
    product_spec: Mapped[str | None] = mapped_column("规格", Text, nullable=True)
    product_name: Mapped[str] = mapped_column("商品名称", Text, nullable=False)
    product_status: Mapped[str] = mapped_column("商品状态", Text, nullable=False)
    inventory_qty: Mapped[Decimal] = mapped_column("库存数量", Numeric(14, 2), nullable=False)
    retail_price: Mapped[Decimal] = mapped_column("零售价", Numeric(14, 4), nullable=False)
    retail_amount: Mapped[Decimal] = mapped_column("零售金额", Numeric(14, 2), nullable=False)
    cost_price: Mapped[Decimal] = mapped_column("成本价", Numeric(14, 4), nullable=False)
    inventory_amount: Mapped[Decimal] = mapped_column("库存金额", Numeric(14, 2), nullable=False)
    untaxed_cost_amount: Mapped[Decimal] = mapped_column(
        "未税成本金额", Numeric(14, 2), nullable=False
    )
    gross_margin_rate: Mapped[Decimal] = mapped_column("毛利率", Numeric(5, 2), nullable=False)
    # 大包装数量在真实数据中可能出现“2条9包”等文本，因此保留为字符串。
    large_package_qty: Mapped[str | None] = mapped_column("大包装数量", Text, nullable=True)
    purchase_in_transit_qty: Mapped[Decimal] = mapped_column(
        "采购在途数量", Numeric(14, 3), nullable=False
    )
    sales_in_transit_qty: Mapped[Decimal] = mapped_column(
        "销售在途数量", Numeric(14, 3), nullable=False
    )
    requisition_in_transit_qty: Mapped[Decimal] = mapped_column(
        "要货在途数量", Numeric(14, 3), nullable=False
    )
    transfer_in_transit_qty: Mapped[Decimal] = mapped_column(
        "调拨在途数量", Numeric(14, 3), nullable=False
    )
    distribution_in_transit_qty: Mapped[Decimal] = mapped_column(
        "配送在途数量", Numeric(14, 3), nullable=False
    )
    return_in_transit_qty: Mapped[Decimal] = mapped_column(
        "配退在途数量", Numeric(14, 3), nullable=False
    )
    min_inventory_qty: Mapped[Decimal] = mapped_column(
        "最小库存量", Numeric(14, 3), nullable=False
    )
    max_inventory_qty: Mapped[Decimal] = mapped_column(
        "最大库存量", Numeric(14, 3), nullable=False
    )
    turnover_days: Mapped[Decimal] = mapped_column("周转天数", Numeric(14, 2), nullable=False)
    last_sale_date: Mapped[date | None] = mapped_column("最后一次销售日期", Date, nullable=True)
    last_purchase_date: Mapped[date | None] = mapped_column(
        "最后一次进货日期", Date, nullable=True
    )
