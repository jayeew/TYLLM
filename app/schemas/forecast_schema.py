from decimal import Decimal

from app.schemas.common import AppBaseModel


class ForecastCalculationRequest(AppBaseModel):
    store_code: str | None = None
    sku: Decimal | None = None


class ForecastCalculationResponse(AppBaseModel):
    success: bool
    calculated_count: int
    generated_count: int
    message: str


class ForecastItem(AppBaseModel):
    id: int
    store_code: str
    product_category: str
    product_name: str
    sku: Decimal
    product_brand: str | None = None
    product_spec: Decimal | None = None
    suggested_replenishment_date: int
    suggested_qty: Decimal
    main_supplier_name: str | None = None
    supplier_code: Decimal | None = None
    warehouse: str | None = None
    estimated_arrival_time: int


class ForecastListResponse(AppBaseModel):
    items: list[ForecastItem]
