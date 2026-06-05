from decimal import Decimal
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """集中管理应用配置，并支持从 .env 覆盖默认值。"""

    app_name: str = "inventory-forecast-demo"
    api_prefix: str = "/api/v1"
    alert_correction_factor: Decimal = Decimal("1")

    alert_factor_k0_phase1: Decimal = Decimal("1.0")
    alert_factor_k0_phase2: Decimal = Decimal("1.0")
    alert_factor_k0_phase3: Decimal = Decimal("1.0")

    alert_factor_k1_workday: Decimal = Decimal("1.0")
    alert_factor_k1_weekend: Decimal = Decimal("1.0")
    alert_factor_k1_holiday: Decimal = Decimal("1.0")
    alert_factor_k1_peak: Decimal = Decimal("1.0")
    weight_k1: Decimal = Decimal("1.0")

    alert_factor_k2_down: Decimal = Decimal("1.0")
    alert_factor_k2_stable: Decimal = Decimal("1.0")
    alert_factor_k2_up: Decimal = Decimal("1.0")
    alert_factor_k2_fastup: Decimal = Decimal("1.0")
    weight_k2: Decimal = Decimal("1.0")

    database_url_override: str | None = Field(default=None, validation_alias="DATABASE_URL")
    postgres_recordmanager_host: str = "localhost"
    postgres_recordmanager_port: int = 5432
    postgres_recordmanager_database: str = "inventory_forecast_demo"
    postgres_recordmanager_user: str = "postgres"
    postgres_recordmanager_password: str = "postgres"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        """生成 SQLAlchemy 使用的数据库连接串。"""
        # 如果环境变量提供了完整 DATABASE_URL，优先使用它，避免重复拼接。
        if self.database_url_override:
            return self.database_url_override

        # 用户名和密码需要 URL 编码，防止特殊字符破坏连接串格式。
        user = quote_plus(self.postgres_recordmanager_user)
        password = quote_plus(self.postgres_recordmanager_password)
        return (
            "postgresql+psycopg://"
            f"{user}:{password}@"
            f"{self.postgres_recordmanager_host}:"
            f"{self.postgres_recordmanager_port}/"
            f"{self.postgres_recordmanager_database}"
        )


settings = Settings()
