from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import verify_request
from app.core.database import get_db
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
    service = QueryService(db)
    items = service.list_alerts(
        store_code=store_code,
        sku=sku,
        warning_level=warning_level,
        warning_category=warning_category,
    )
    return AlertListResponse(items=items)
