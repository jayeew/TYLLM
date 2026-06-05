from decimal import Decimal

from sqlalchemy import BigInteger, Identity, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AdsInventoryAlert(Base):
    __tablename__ = "ads_inventory_alert"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    store_code: Mapped[str] = mapped_column("门店编号", String, nullable=False)
    sku: Mapped[Decimal] = mapped_column("SKU货号", Numeric(20, 0), nullable=False)
    product_name: Mapped[str] = mapped_column("商品名称", Text, nullable=False)
    warning_category: Mapped[str] = mapped_column("预警类别", Text, nullable=False)
    warning_time: Mapped[int] = mapped_column("预警时间", BigInteger, nullable=False)
    warning_store: Mapped[str] = mapped_column("预警门店", Text, nullable=False)
    warning_product_category: Mapped[str] = mapped_column("预警商品类别", Text, nullable=False)
    warning_level: Mapped[str] = mapped_column("预警级别", Text, nullable=False)
    warning_detail: Mapped[str] = mapped_column("预警详情", Text, nullable=False)
    replenishment_suggestion: Mapped[str | None] = mapped_column("补货建议", Text, nullable=True)
