from __future__ import annotations

from typing import Any

from app.mappers.view_sales_daily_clean import ViewSalesDailyClean as Sales
from app.repositories.clickhouse_base import ClickHouseRepository


class SalesDailyRepo(ClickHouseRepository):
    """view_sales_daily_clean 访问仓储。"""

    def list_records(
        self,
        org_code: str | None = None,
        sku: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        where_parts: list[str] = []
        params: dict[str, Any] = {
            "limit": limit or self.settings.clickhouse_sales_daily_query_limit,
        }

        if org_code:
            where_parts.append(
                f"toString({Sales.field('org_code')}) = {{org_code:String}}"
            )
            params["org_code"] = org_code
        if sku:
            where_parts.append(f"toString({Sales.field('sku')}) = {{sku:String}}")
            params["sku"] = sku

        query = (
            f"SELECT {Sales.select_clause()} "
            f"FROM {self.settings.clickhouse_sales_daily_table} AS {Sales.alias} "
            f"{self._where_clause(where_parts)}"
            f"ORDER BY {Sales.field('sale_date')} DESC, "
            f"{Sales.field('org_code')}, {Sales.field('sku')} "
            "LIMIT {limit:UInt64}"
        )
        return self._query_dicts(query, params)

    @staticmethod
    def _where_clause(where_parts: list[str]) -> str:
        return f"WHERE {' AND '.join(where_parts)} " if where_parts else ""
