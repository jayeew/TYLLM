import argparse
import json
from decimal import Decimal
from typing import Any

from app.config.database import get_clickhouse_client
from app.services.alert_service import AlertService
from app.services.forecast_service import ForecastService
from app.tasks.demo_runner import run_demo


def decimal_default(value: Any) -> int | float | str:
    """把脚本输出中的 Decimal 转成 JSON 可序列化类型。"""
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    return str(value)


def parse_args() -> argparse.Namespace:
    """解析本地脚本命令行参数。"""
    parser = argparse.ArgumentParser(
        description="本地触发库存预警和补货需求预测占位流程，不依赖 FastAPI 服务进程。",
    )
    parser.add_argument(
        "--mode",
        choices=("all", "alerts", "forecasts"),
        default="all",
        help="触发模式：all=预警+预测占位，alerts=仅预警占位，forecasts=仅补货预测占位。",
    )
    parser.add_argument(
        "--org-code",
        default=None,
        help="可选，机构编码；不传则读取销售视图中的记录。",
    )
    parser.add_argument(
        "--sku",
        default=None,
        help="可选，商品编码/SKU；不传则处理全部商品。",
    )
    return parser.parse_args()


def run_local(
    mode: str,
    org_code: str | None,
    sku: str | None,
) -> dict:
    """按指定模式执行本地触发任务。"""
    db = get_clickhouse_client()
    if mode == "alerts":
        return {
            "alerts": AlertService(db).scan_alerts(
                org_code=org_code,
                sku=sku,
            )
        }
    if mode == "forecasts":
        return {
            "forecasts": ForecastService(db).calculate_forecasts(
                org_code=org_code,
                sku=sku,
            )
        }
    return run_demo(
        db=db,
        org_code=org_code,
        sku=sku,
    )


def main() -> None:
    """本地脚本入口：解析参数、执行任务、打印 JSON 结果。"""
    args = parse_args()
    result = run_local(
        mode=args.mode,
        org_code=args.org_code,
        sku=args.sku,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=decimal_default))


if __name__ == "__main__":
    main()
