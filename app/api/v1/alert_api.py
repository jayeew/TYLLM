from datetime import date

from fastapi import APIRouter, Depends
from fastapi import Query

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
    """手动触发库存预警扫描流程。"""
    service = AlertService(db)
    result = service.scan_alerts(
        org_code=payload.org_code,
        sku=payload.sku,
        calc_date=payload.calc_date,
        limit=payload.limit,
    )
    return AlertScanResponse(**result)


@router.get("", response_model=AlertListResponse)
def list_alerts(
    run_id: str | None = None,
    calc_date: date | None = None,
    org_code: str | None = None,
    sku: str | None = None,
    limit: int | None = Query(default=None, ge=1),
    db: ClickHouseClient = Depends(get_db),
) -> AlertListResponse:
    """查询库存预警结果。"""
    items = QueryService(db).list_alerts(
        run_id=run_id,
        calc_date=calc_date,
        org_code=org_code,
        sku=sku,
        limit=limit,
    )
    return AlertListResponse(items=items)
