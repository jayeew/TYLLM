from collections.abc import Generator
import os
from typing import Any

from app.config.config import settings


ClickHouseClient = Any
_client: ClickHouseClient | None = None


def ensure_clickhouse_no_proxy(host: str) -> None:
    """确保内网 ClickHouse 地址不走 HTTP 代理。"""
    for key in ("NO_PROXY", "no_proxy"):
        current = os.environ.get(key, "")
        parts = [part.strip() for part in current.split(",") if part.strip()]
        if host not in parts:
            parts.append(host)
            os.environ[key] = ",".join(parts)


def get_clickhouse_client() -> ClickHouseClient:
    """返回应用共享的 ClickHouse 客户端连接。"""
    global _client
    if _client is None:
        ensure_clickhouse_no_proxy(settings.clickhouse_host)
        try:
            import clickhouse_connect
        except ImportError as exc:
            raise RuntimeError(
                "当前项目固定使用 ClickHouse，请先安装依赖：pip install -r requirements.txt"
            ) from exc

        _client = clickhouse_connect.get_client(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            username=settings.clickhouse_user,
            password=settings.clickhouse_password,
            database=settings.clickhouse_database,
            secure=settings.clickhouse_secure,
            connect_timeout=settings.clickhouse_connect_timeout,
            send_receive_timeout=settings.clickhouse_send_receive_timeout,
        )
    return _client


def get_db() -> Generator[ClickHouseClient, None, None]:
    """为 FastAPI 请求提供 ClickHouse 客户端。"""
    yield get_clickhouse_client()
