from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.mappers.dim_base_info import DimBaseInfo


@dataclass(frozen=True)
class StoreMapping:
    """机构编码到门店编号、门店名称的映射结果。"""

    org_code: Decimal
    store_code: str
    store_name: str


class BaseInfoRepo:
    """基础门店信息数据访问对象。"""

    def __init__(self, db: Session) -> None:
        """保存当前请求中的数据库会话。"""
        self.db = db

    def list_store_names(self, store_codes: list[str]) -> dict[str, str]:
        """按门店编号批量查询门店名称。"""
        if not store_codes:
            return {}

        # 查询结果转成字典，方便服务层按门店编号快速取名称。
        stmt = select(DimBaseInfo.store_code, DimBaseInfo.store_name).where(
            DimBaseInfo.store_code.in_(store_codes)
        )
        rows = self.db.execute(stmt).all()
        return {store_code: store_name for store_code, store_name in rows}

    def list_store_mappings_by_org_codes(
        self,
        org_codes: list[Decimal],
    ) -> dict[Decimal, StoreMapping]:
        """按机构编码批量查询门店映射信息。"""
        if not org_codes:
            return {}

        stmt = select(
            DimBaseInfo.org_code,
            DimBaseInfo.store_code,
            DimBaseInfo.store_name,
        ).where(DimBaseInfo.org_code.in_(org_codes))
        rows = self.db.execute(stmt).all()
        # 库存表按机构编码组织，POS 表按门店编号组织，服务层需要这个映射来查销量。
        return {
            org_code: StoreMapping(
                org_code=org_code,
                store_code=store_code,
                store_name=store_name,
            )
            for org_code, store_code, store_name in rows
            if org_code is not None
        }

    def get_org_code_by_store_code(self, store_code: str) -> Decimal | None:
        """把接口传入的门店编号转换成库存表使用的机构编码。"""
        stmt = select(DimBaseInfo.org_code).where(DimBaseInfo.store_code == store_code)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_store_code_by_org_code(self, org_code: Decimal) -> str | None:
        """把机构编码转换成结果表和接口常用的门店编号。"""
        stmt = select(DimBaseInfo.store_code).where(DimBaseInfo.org_code == org_code)
        return self.db.execute(stmt).scalar_one_or_none()
