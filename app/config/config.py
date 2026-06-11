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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
