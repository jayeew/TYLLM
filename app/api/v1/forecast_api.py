from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import verify_request
from app.config.database import get_db
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
    db: Session = Depends(get_db),
) -> ForecastCalculationResponse:
    """手动触发补货需求预测，并返回本次计算统计。"""
    service = ForecastService(db)
    result = service.calculate_forecasts(store_code=payload.store_code, sku=payload.sku)
    return ForecastCalculationResponse(**result)


@router.get("", response_model=ForecastListResponse)
def list_forecasts(
    store_code: str | None = Query(default=None),
    sku: Decimal | None = Query(default=None),
    product_category: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ForecastListResponse:
    """按门店、SKU、类别或仓库查询已生成的补货预测结果。"""
    service = QueryService(db)
    items = service.list_forecasts(
        store_code=store_code,
        sku=sku,
        product_category=product_category,
        warehouse=warehouse,
    )
    return ForecastListResponse(items=items)
