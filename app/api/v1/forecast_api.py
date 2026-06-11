from datetime import date

from fastapi import APIRouter, Depends
from fastapi import Query

from app.api.deps import verify_request
from app.config.database import ClickHouseClient, get_db
from app.schemas.forecast_schema import (
    ForecastCalculationRequest,
    ForecastCalculationResponse,
    ForecastListResponse,
)
from app.services.forecast_service import ForecastService
from app.services.query_service import QueryService


router = APIRouter(dependencies=[Depends(verify_request)])


@router.post("/calculate", response_model=ForecastCalculationResponse)
def calculate_forecasts(
    payload: ForecastCalculationRequest,
    db: ClickHouseClient = Depends(get_db),
) -> ForecastCalculationResponse:
    """手动触发补货需求预测流程。"""
    service = ForecastService(db)
    result = service.calculate_forecasts(
        org_code=payload.org_code,
        sku=payload.sku,
        calc_date=payload.calc_date,
        limit=payload.limit,
    )
    return ForecastCalculationResponse(**result)


@router.get("", response_model=ForecastListResponse)
def list_forecasts(
    run_id: str | None = None,
    calc_date: date | None = None,
    org_code: str | None = None,
    sku: str | None = None,
    limit: int | None = Query(default=None, ge=1),
    db: ClickHouseClient = Depends(get_db),
) -> ForecastListResponse:
    """查询补货预测结果。"""
    items = QueryService(db).list_forecasts(
        run_id=run_id,
        calc_date=calc_date,
        org_code=org_code,
        sku=sku,
        limit=limit,
    )
    return ForecastListResponse(items=items)
