from __future__ import annotations

from typing import Any

from app.mappers.dim_product import DimProduct as Product
from app.repositories.clickhouse_base import ClickHouseRepository


class DimProductRepo(ClickHouseRepository):
    """dim_product 访问仓储。"""

    def list_records(
        self,
        product_code: str | None = None,
        international_barcode: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        where_parts: list[str] = []
        params: dict[str, Any] = {
            "limit": limit or self.settings.clickhouse_dim_product_query_limit,
        }

        if product_code:
            where_parts.append(
                f"toString({Product.field('product_code')}) = {{product_code:String}}"
            )
            params["product_code"] = product_code
        if international_barcode:
            where_parts.append(
                "toString("
                f"{Product.field('international_barcode')}"
                ") = {international_barcode:String}"
            )
            params["international_barcode"] = international_barcode

        query = (
            f"SELECT {Product.select_clause()} "
            f"FROM {self.settings.clickhouse_dim_product_table} AS {Product.alias} "
            f"{self._where_clause(where_parts)}"
            f"ORDER BY {Product.field('product_code')} "
            "LIMIT {limit:UInt64}"
        )
        return self._query_dicts(query, params)

    @staticmethod
    def _where_clause(where_parts: list[str]) -> str:
        return f"WHERE {' AND '.join(where_parts)} " if where_parts else ""
