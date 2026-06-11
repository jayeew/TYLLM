from fastapi import APIRouter, Depends

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
    """手动触发补货需求预测占位流程。"""
    service = ForecastService(db)
    result = service.calculate_forecasts(org_code=payload.org_code, sku=payload.sku)
    return ForecastCalculationResponse(**result)


@router.get("", response_model=ForecastListResponse)
def list_forecasts() -> ForecastListResponse:
    """查询补货预测占位结果。"""
    items = QueryService().list_forecasts()
    return ForecastListResponse(items=items)
