from decimal import Decimal

from sqlalchemy import BigInteger, Identity, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.mappers.base import Base


class DimBaseInfo(Base):
    """门店基础信息表，用于把机构编码映射为业务侧门店编号。"""

    __tablename__ = "dim_base_info"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    service_area: Mapped[str] = mapped_column("所属服务区", Text, nullable=False)
    # 库存快照表使用机构编码，而 POS 流水使用门店编号，二者需要通过此表桥接。
    org_code: Mapped[Decimal | None] = mapped_column("机构编码", Numeric, nullable=True)
    service_direction: Mapped[str | None] = mapped_column("服务区方向", Text, nullable=True)
    store_code: Mapped[str] = mapped_column("门店编号", String, nullable=False)
    store_name: Mapped[str] = mapped_column("门店名称", Text, nullable=False)
    camera_code: Mapped[str | None] = mapped_column("摄像机编号", String, nullable=True)
    camera_name: Mapped[str | None] = mapped_column("摄像机名称", Text, nullable=True)
