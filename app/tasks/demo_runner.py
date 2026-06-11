from app.config.database import ClickHouseClient
from app.services.alert_service import AlertService
from app.services.forecast_service import ForecastService


def run_demo(
    db: ClickHouseClient,
    org_code: str | None = None,
    sku: str | None = None,
) -> dict:
    """批量执行预警和补货预测占位流程，便于脚本或定时任务复用。"""
    # 当前仅触发销售视图读取和规则占位，不生成可用业务结果。
    alert_result = AlertService(db).scan_alerts(org_code=org_code, sku=sku)
    forecast_result = ForecastService(db).calculate_forecasts(org_code=org_code, sku=sku)
    return {
        "alerts": alert_result,
        "forecasts": forecast_result,
    }
