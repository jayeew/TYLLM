import argparse
import json
from decimal import Decimal, InvalidOperation
from typing import Any

from app.config.database import SessionLocal
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
    def parse_decimal(value: str) -> Decimal:
        """把命令行传入的 SKU 转成 Decimal，并输出友好的参数错误。"""
        try:
            return Decimal(value)
        except InvalidOperation as exc:
            raise argparse.ArgumentTypeError("sku 必须是数字") from exc

    parser = argparse.ArgumentParser(
        description="本地触发库存预警扫描和补货需求预测，不依赖 FastAPI 服务进程。",
    )
    parser.add_argument(
        "--mode",
        choices=("all", "alerts", "forecasts"),
        default="all",
        help="触发模式：all=预警+预测，alerts=仅库存预警，forecasts=仅补货预测。",
    )
    parser.add_argument(
        "--store-code",
        default=None,
        help="可选，门店编号或机构编码；不传则处理全部库存快照。",
    )
    parser.add_argument(
        "--sku",
        type=parse_decimal,
        default=None,
        help="可选，商品编码/SKU；不传则处理全部商品。",
    )
    return parser.parse_args()


def run_local(mode: str, store_code: str | None, sku: Decimal | None) -> dict:
    """按指定模式执行本地触发任务。"""
    # 本地脚本自己创建并关闭 Session，不复用 FastAPI 的依赖注入链路。
    with SessionLocal() as db:
        if mode == "alerts":
            return {
                "alerts": AlertService(db).scan_alerts(
                    store_code=store_code,
                    sku=sku,
                )
            }
        if mode == "forecasts":
            return {
                "forecasts": ForecastService(db).calculate_forecasts(
                    store_code=store_code,
                    sku=sku,
                )
            }
        return run_demo(db=db, store_code=store_code, sku=sku)


def main() -> None:
    """本地脚本入口：解析参数、执行任务、打印 JSON 结果。"""
    args = parse_args()
    result = run_local(
        mode=args.mode,
        store_code=args.store_code,
        sku=args.sku,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=decimal_default))


if __name__ == "__main__":
    main()
