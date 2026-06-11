from __future__ import annotations

from datetime import date
from typing import Any

from app.mappers.dim_product import DimProduct as Product
from app.mappers.dwd_product_stock import DwdProductStock as Stock
from app.mappers.view_sales_daily_clean import ViewSalesDailyClean as Sales
from app.repositories.clickhouse_base import ClickHouseRepository


class InventoryCalculationRepo(ClickHouseRepository):
    """预警和补货共用的计算输入仓储。"""

    def list_inputs(
        self,
        calc_date: date,
        org_code: str | None = None,
        product_code: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        where_parts, params = self._build_filters(
            calc_date=calc_date,
            org_code=org_code,
            product_code=product_code,
            limit=limit,
        )
        sales_subquery = self._sales_averages_subquery()

        query = (
            f"SELECT {self._select_clause()} "
            f"FROM {self.settings.clickhouse_product_stock_table} AS {Stock.alias} "
            f"ANY LEFT JOIN {self.settings.clickhouse_dim_product_table} AS {Product.alias} "
            f"ON toString({Product.field('product_code')}) = "
            f"toString({Stock.field('product_code')}) "
            f"LEFT JOIN ({sales_subquery}) AS sa "
            f"ON sa.org_code = toString({Stock.field('org_code')}) "
            f"AND sa.product_code = toString({Stock.field('product_code')}) "
            f"{self._where_clause(where_parts)}"
            f"ORDER BY {Stock.field('org_code')}, {Stock.field('product_code')} "
            "LIMIT {limit:UInt64}"
        )
        return self._query_dicts(query, params)

    def _build_filters(
        self,
        *,
        calc_date: date,
        org_code: str | None,
        product_code: str | None,
        limit: int | None,
    ) -> tuple[list[str], dict[str, Any]]:
        where_parts: list[str] = []
        params: dict[str, Any] = {
            "calc_date": calc_date,
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

        return where_parts, params

    @staticmethod
    def _where_clause(where_parts: list[str]) -> str:
        return f"WHERE {' AND '.join(where_parts)} " if where_parts else ""

    @staticmethod
    def _decimal_zero() -> str:
        return "CAST(0, 'Decimal(18, 4)')"

    def _sales_averages_subquery(self) -> str:
        sales_date = Sales.field("sale_date")
        sales_qty = Sales.field("sales_qty")
        sales_org = Sales.field("org_code")
        sales_sku = Sales.field("sku")

        return (
            "SELECT "
            f"toString({sales_org}) AS org_code, "
            f"toString({sales_sku}) AS product_code, "
            f"{self._sales_average_expr(days=7)} AS sales_avg_7, "
            f"{self._sales_average_expr(days=15)} AS sales_avg_15, "
            f"{self._sales_average_expr(days=30)} AS sales_avg_30 "
            f"FROM {self.settings.clickhouse_sales_daily_table} AS {Sales.alias} "
            f"WHERE {sales_date} >= addDays({{calc_date:Date}}, -30) "
            f"AND {sales_date} < {{calc_date:Date}} "
            f"GROUP BY toString({sales_org}), toString({sales_sku})"
        )

    @staticmethod
    def _sales_average_expr(*, days: int) -> str:
        sales_date = Sales.field("sale_date")
        sales_qty = Sales.field("sales_qty")
        return (
            "CAST(round(ifNull(sumIf(toFloat64("
            f"{sales_qty}), {sales_date} >= addDays({{calc_date:Date}}, -{days}) "
            "AND "
            f"{sales_date} < {{calc_date:Date}}), 0) / {days}, 4), "
            "'Decimal(18, 4)')"
        )

    def _select_clause(self) -> str:
        columns = [
            (Stock.field("org_code"), "org_code"),
            (Stock.field("org_name"), "org_name"),
            (Stock.field("product_code"), "product_code"),
            (Stock.field("international_barcode"), "international_barcode"),
            (Stock.field("product_category_code"), "product_category_code"),
            (Stock.field("product_category_name"), "product_category_name"),
            (Stock.field("supplier_name"), "supplier_name"),
            (Stock.field("unit"), "unit"),
            (Stock.field("product_name"), "product_name"),
            (Stock.field("product_status"), "product_status"),
            (Stock.field("inventory_qty"), "inventory_qty"),
            (Stock.field("large_package_qty"), "large_package_qty"),
            (Stock.field("purchase_in_transit_qty"), "purchase_in_transit_qty"),
            (Stock.field("sales_in_transit_qty"), "sales_in_transit_qty"),
            (Stock.field("requisition_in_transit_qty"), "requisition_in_transit_qty"),
            (Stock.field("transfer_in_transit_qty"), "transfer_in_transit_qty"),
            (Stock.field("distribution_in_transit_qty"), "distribution_in_transit_qty"),
            (
                Stock.field("distribution_out_transit_qty"),
                "distribution_out_transit_qty",
            ),
            (Stock.field("min_inventory_qty"), "min_inventory_qty"),
            (Stock.field("max_inventory_qty"), "max_inventory_qty"),
            (Product.field("product_created_at"), "product_created_at"),
            (Product.field("purchase_factor"), "purchase_factor"),
            (Product.field("category_code"), "dim_category_code"),
            (Product.field("product_category"), "dim_product_category"),
            (Product.field("shelf_life_days"), "shelf_life_days"),
            (
                f"ifNull(sa.sales_avg_7, {self._decimal_zero()})",
                "sales_avg_7",
            ),
            (
                f"ifNull(sa.sales_avg_15, {self._decimal_zero()})",
                "sales_avg_15",
            ),
            (
                f"ifNull(sa.sales_avg_30, {self._decimal_zero()})",
                "sales_avg_30",
            ),
        ]
        return ", ".join(f"{expression} AS {alias}" for expression, alias in columns)
