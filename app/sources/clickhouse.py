from __future__ import annotations

from typing import Any

from app.config.config import Settings
from app.config.database import ensure_clickhouse_no_proxy
from app.mappers.view_sales_daily_clean import ViewSalesDailyClean


class ClickHouseSchemaError(RuntimeError):
    """ClickHouse 源视图字段无法满足读取输入时抛出。"""


class ClickHouseSourceRepo:
    """从远端 ClickHouse 读取 view_sales_daily_clean。"""

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self.settings = settings
        self._client: Any | None = client

    @property
    def client(self) -> Any:
        """延迟创建 ClickHouse 连接。"""
        if self._client is None:
            ensure_clickhouse_no_proxy(self.settings.clickhouse_host)
            try:
                import clickhouse_connect
            except ImportError as exc:
                raise RuntimeError(
                    "当前项目固定使用 ClickHouse，请先安装依赖：pip install -r requirements.txt"
                ) from exc

            self._client = clickhouse_connect.get_client(
                host=self.settings.clickhouse_host,
                port=self.settings.clickhouse_port,
                username=self.settings.clickhouse_user,
                password=self.settings.clickhouse_password,
                database=self.settings.clickhouse_database,
                secure=self.settings.clickhouse_secure,
                connect_timeout=self.settings.clickhouse_connect_timeout,
                send_receive_timeout=self.settings.clickhouse_send_receive_timeout,
            )
        return self._client

    def list_sales_daily_records(
        self,
        org_code: str | None = None,
        sku: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """读取 view_sales_daily_clean 原始日销售记录，不附加业务计算。"""
        where_parts: list[str] = []
        params: dict[str, Any] = {
            "limit": limit or self.settings.clickhouse_sales_daily_query_limit,
        }

        if org_code:
            where_parts.append(f"toString({self._sales_expr('org_code')}) = {{org_code:String}}")
            params["org_code"] = org_code
        if sku:
            where_parts.append(f"toString({self._sales_expr('sku')}) = {{sku:String}}")
            params["sku"] = sku

        where_clause = f"WHERE {' AND '.join(where_parts)} " if where_parts else ""
        query = (
            f"SELECT {self._sales_select_clause()} "
            f"FROM {self._sales_daily_table()} AS v "
            f"{where_clause}"
            f"ORDER BY {self._sales_expr('sale_date')} DESC, "
            f"{self._sales_expr('org_code')}, {self._sales_expr('sku')} "
            "LIMIT {limit:UInt64}"
        )
        return self._query_dicts(query, params)

    def _query_dicts(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """执行查询并返回字典行。"""
        result = self.client.query(query, parameters=params)
        return [
            dict(zip(result.column_names, row, strict=False))
            for row in result.result_rows
        ]

    def _sales_select_clause(self) -> str:
        return ", ".join(
            f"{self._sales_expr(field_name)} AS {self._quote_identifier(field_name)}"
            for field_name in ViewSalesDailyClean.columns
        )

    def _sales_daily_table(self) -> str:
        return self._quote_table_name(self.settings.clickhouse_sales_daily_table)

    def _sales_expr(self, field_name: str) -> str:
        try:
            column_name = ViewSalesDailyClean.columns[field_name]
        except KeyError as exc:
            raise ClickHouseSchemaError(f"没有为字段 {field_name} 配置 view_sales_daily_clean 列名") from exc
        return f"v.{self._quote_identifier(column_name)}"

    def _quote_table_name(self, table_name: str) -> str:
        return ".".join(
            self._quote_identifier(part)
            for part in table_name.split(".")
            if part
        )

    def _quote_identifier(self, identifier: str) -> str:
        return f"`{identifier.replace('`', '``')}`"
