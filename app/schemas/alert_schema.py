from decimal import Decimal

from app.schemas.common import AppBaseModel


class AlertScanRequest(AppBaseModel):
    store_code: str | None = None
    sku: Decimal | None = None


class AlertScanResponse(AppBaseModel):
    success: bool
    scanned_count: int
    generated_count: int
    message: str


class AlertItem(AppBaseModel):
    id: int
    store_code: str
    sku: Decimal
    product_name: str
    warning_category: str
    warning_time: int
    warning_store: str
    warning_product_category: str
    warning_level: str
    warning_detail: str
    replenishment_suggestion: str | None = None


class AlertListResponse(AppBaseModel):
    items: list[AlertItem]
