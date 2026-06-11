from __future__ import annotations

from app.repositories.result_columns import (
    ALERT_RESULT_INSERT_COLUMNS,
    ALERT_RESULT_SELECT_COLUMNS,
)
from app.repositories.result_table_repo import ResultTableRepo
from app.repositories.result_table_sql import CREATE_ALERT_RESULT_TABLE_SQL


class InventoryAlertResultRepo(ResultTableRepo):
    """ads_inventory_alert_result 结果表仓储。"""

    table_name_setting = "clickhouse_alert_result_table"
    create_table_sql = CREATE_ALERT_RESULT_TABLE_SQL
    create_table_placeholder = "alert_result_table"
    insert_columns = ALERT_RESULT_INSERT_COLUMNS
    select_columns = ALERT_RESULT_SELECT_COLUMNS
