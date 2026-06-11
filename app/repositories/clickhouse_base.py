from __future__ import annotations

from typing import Any

from app.config.config import Settings, settings
from app.config.database import ClickHouseClient


class ClickHouseRepository:
    """ClickHouse 仓储基类，只放通用数据库读写动作。"""

    def __init__(
        self,
        db: ClickHouseClient,
        repo_settings: Settings | None = None,
    ) -> None:
        self.db = db
        self.settings = repo_settings or settings

    def _query_dicts(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        result = self.db.query(query, parameters=params)
        return [
            dict(zip(result.column_names, row, strict=False))
            for row in result.result_rows
        ]

    def _insert_rows(
        self,
        table_name: str,
        columns: list[str],
        rows: list[dict[str, Any]],
    ) -> int:
        if not rows:
            return 0

        data = [
            [row.get(column_name) for column_name in columns]
            for row in rows
        ]
        self.db.insert(table_name, data, column_names=columns)
        return len(data)
