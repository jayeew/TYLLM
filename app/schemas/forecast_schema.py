from decimal import Decimal

from app.schemas.common import AppBaseModel


class ForecastCalculationRequest(AppBaseModel):
    """补货预测计算请求，可按门店和 SKU 缩小计算范围。"""

    store_code: str | None = None
    sku: Decimal | None = None


class ForecastCalculationResponse(AppBaseModel):
    """补货预测计算结果统计。"""

    success: bool
    calculated_count: int
    generated_count: int
    skipped_count: int = 0
    message: str


class ForecastItem(AppBaseModel):
    """单条补货预测查询结果。"""

    id: int
    store_code: str
    product_category: str
    product_name: str
    sku: Decimal
    product_brand: str | None = None
    product_spec: str | None = None
    suggested_replenishment_date: int
    suggested_qty: Decimal
    main_supplier_name: str | None = None
    supplier_code: Decimal | None = None
    warehouse: str | None = None
    estimated_arrival_time: int


class ForecastListResponse(AppBaseModel):
    """补货预测列表响应。"""

    items: list[ForecastItem]
