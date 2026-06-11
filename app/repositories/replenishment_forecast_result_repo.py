from __future__ import annotations

from app.repositories.result_columns import (
    FORECAST_RESULT_INSERT_COLUMNS,
    FORECAST_RESULT_SELECT_COLUMNS,
)
from app.repositories.result_table_repo import ResultTableRepo
from app.repositories.result_table_sql import CREATE_FORECAST_RESULT_TABLE_SQL


class ReplenishmentForecastResultRepo(ResultTableRepo):
    """ads_replenishment_forecast_result 结果表仓储。"""

    table_name_setting = "clickhouse_forecast_result_table"
    create_table_sql = CREATE_FORECAST_RESULT_TABLE_SQL
    create_table_placeholder = "forecast_result_table"
    insert_columns = FORECAST_RESULT_INSERT_COLUMNS
    select_columns = FORECAST_RESULT_SELECT_COLUMNS
