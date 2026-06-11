from fastapi import APIRouter, Depends

from app.api.deps import verify_request
from app.config.database import ClickHouseClient, get_db
from app.schemas.alert_schema import (
    AlertListResponse,
    AlertScanRequest,
    AlertScanResponse,
)
from app.services.alert_service import AlertService
from app.services.query_service import QueryService


router = APIRouter(dependencies=[Depends(verify_request)])


@router.post("/scan", response_model=AlertScanResponse)
def scan_alerts(
    payload: AlertScanRequest,
    db: ClickHouseClient = Depends(get_db),
) -> AlertScanResponse:
    """手动触发库存预警扫描占位流程。"""
    service = AlertService(db)
    result = service.scan_alerts(org_code=payload.org_code, sku=payload.sku)
    return AlertScanResponse(**result)


@router.get("", response_model=AlertListResponse)
def list_alerts() -> AlertListResponse:
    """查询库存预警占位结果。"""
    items = QueryService().list_alerts()
    return AlertListResponse(items=items)
