from __future__ import annotations

from typing import Any

from app.mappers.dwd_product_stock import DwdProductStock as Stock
from app.repositories.clickhouse_base import ClickHouseRepository


class ProductStockRepo(ClickHouseRepository):
    """dwd_product_stock 访问仓储。"""

    def list_records(
        self,
        org_code: str | None = None,
        product_code: str | None = None,
        international_barcode: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        where_parts: list[str] = []
        params: dict[str, Any] = {
            "limit": limit or self.settings.clickhouse_product_stock_query_limit,
        }

        if org_code:
            where_parts.append(
                f"toString({Stock.field('org_code')}) = {{org_code:String}}"
            )
            params["org_code"] = org_code
        if product_code:
            where_parts.append(
                f"toString({Stock.field('product_code')}) = {{product_code:String}}"
            )
            params["product_code"] = product_code
        if international_barcode:
            where_parts.append(
                "toString("
                f"{Stock.field('international_barcode')}"
                ") = {international_barcode:String}"
            )
            params["international_barcode"] = international_barcode

        query = (
            f"SELECT {Stock.select_clause()} "
            f"FROM {self.settings.clickhouse_product_stock_table} AS {Stock.alias} "
            f"{self._where_clause(where_parts)}"
            f"ORDER BY {Stock.field('org_code')}, {Stock.field('product_code')} "
            "LIMIT {limit:UInt64}"
        )
        return self._query_dicts(query, params)

    @staticmethod
    def _where_clause(where_parts: list[str]) -> str:
        return f"WHERE {' AND '.join(where_parts)} " if where_parts else ""
