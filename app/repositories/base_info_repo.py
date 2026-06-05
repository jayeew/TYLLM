from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dim_base_info import DimBaseInfo


class BaseInfoRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_store_names(self, store_codes: list[str]) -> dict[str, str]:
        if not store_codes:
            return {}

        stmt = select(DimBaseInfo.store_code, DimBaseInfo.store_name).where(
            DimBaseInfo.store_code.in_(store_codes)
        )
        rows = self.db.execute(stmt).all()
        return {store_code: store_name for store_code, store_name in rows}
