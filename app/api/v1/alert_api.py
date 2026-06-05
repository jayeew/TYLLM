from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import verify_request
from app.config.database import get_db
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
    db: Session = Depends(get_db),
) -> AlertScanResponse:
    """手动触发库存预警扫描，并返回本次扫描统计。"""
    service = AlertService(db)
    result = service.scan_alerts(store_code=payload.store_code, sku=payload.sku)
    return AlertScanResponse(**result)


@router.get("", response_model=AlertListResponse)
def list_alerts(
    store_code: str | None = Query(default=None),
    sku: Decimal | None = Query(default=None),
    warning_level: str | None = Query(default=None),
    warning_category: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> AlertListResponse:
    """按门店、SKU、预警级别或类别查询已生成的库存预警。"""
    service = QueryService(db)
    items = service.list_alerts(
        store_code=store_code,
        sku=sku,
        warning_level=warning_level,
        warning_category=warning_category,
    )
    return AlertListResponse(items=items)
