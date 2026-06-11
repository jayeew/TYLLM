from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """集中管理应用配置；业务变量和因子必须通过 .env 提供。"""

    app_name: str
    api_prefix: str

    alert_correction_factor: Decimal
    alert_factor_k0_phase1: Decimal
    alert_factor_k0_phase2: Decimal
    alert_factor_k0_phase3: Decimal
    alert_factor_k1_workday: Decimal
    alert_factor_k1_weekend: Decimal
    alert_factor_k1_holiday: Decimal
    alert_factor_k1_peak: Decimal
    weight_k1: Decimal
    alert_factor_k2_down: Decimal
    alert_factor_k2_stable: Decimal
    alert_factor_k2_up: Decimal
    alert_factor_k2_fastup: Decimal
    weight_k2: Decimal

    clickhouse_host: str
    clickhouse_port: int
    clickhouse_database: str
    clickhouse_user: str
    clickhouse_password: str
    clickhouse_secure: bool
    clickhouse_connect_timeout: int
    clickhouse_send_receive_timeout: int
    clickhouse_sales_daily_table: str
    clickhouse_sales_daily_query_limit: int
    clickhouse_dim_product_table: str = "dim_product"
    clickhouse_dim_product_query_limit: int = 1000
    clickhouse_product_stock_table: str = "dwd_product_stock"
    clickhouse_product_stock_query_limit: int = 1000
    clickhouse_alert_result_table: str = "ads_inventory_alert_result"
    clickhouse_forecast_result_table: str = "ads_replenishment_forecast_result"
    clickhouse_result_query_limit: int = 1000

    alert_level1_coverage_days: Decimal = Decimal("14")
    alert_level2_coverage_days: Decimal = Decimal("7")
    alert_level3_coverage_days: Decimal = Decimal("3")
    alert_default_safety_stock_qty: Decimal = Decimal("0")
    alert_expiring_stock_ratio_limit: Decimal = Decimal("0.5")

    replenish_default_purchase_cycle_days: Decimal = Decimal("3")
    replenish_safety_buffer_days: Decimal = Decimal("2")
    replenish_default_min_order_qty: Decimal = Decimal("1")
    replenish_default_pack_qty: Decimal = Decimal("1")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
