from __future__ import annotations

from datetime import date
from typing import Any

from app.repositories.clickhouse_base import ClickHouseRepository


class ResultTableRepo(ClickHouseRepository):
    """结果表仓储基类。"""

    table_name_setting: str
    create_table_sql: str
    create_table_placeholder: str
    insert_columns: list[str]
    select_columns: list[str]

    @property
    def table_name(self) -> str:
        return str(getattr(self.settings, self.table_name_setting))

    def ensure_table(self) -> None:
        self.db.command(
            self.create_table_sql.format(
                **{self.create_table_placeholder: self.table_name}
            )
        )

    def insert_many(self, rows: list[dict[str, Any]]) -> int:
        return self._insert_rows(
            table_name=self.table_name,
            columns=self.insert_columns,
            rows=rows,
        )

    def list_records(
        self,
        run_id: str | None = None,
        calc_date: date | None = None,
        org_code: str | None = None,
        product_code: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        where_parts: list[str] = []
        params: dict[str, Any] = {
            "limit": limit or self.settings.clickhouse_result_query_limit,
        }

        if run_id:
            where_parts.append("toString(run_id) = {run_id:String}")
            params["run_id"] = run_id
        if calc_date:
            where_parts.append("calc_date = {calc_date:Date}")
            params["calc_date"] = calc_date
        if org_code:
            where_parts.append("toString(org_code) = {org_code:String}")
            params["org_code"] = org_code
        if product_code:
            where_parts.append("toString(product_code) = {product_code:String}")
            params["product_code"] = product_code

        where_clause = f"WHERE {' AND '.join(where_parts)} " if where_parts else ""
        select_clause = ", ".join(self.select_columns)
        query = (
            f"SELECT {select_clause} "
            f"FROM {self.table_name} "
            f"{where_clause}"
            "ORDER BY calc_date DESC, created_at DESC, run_id DESC, org_code, product_code "
            "LIMIT {limit:UInt64}"
        )
        return self._query_dicts(query, params)
