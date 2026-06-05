from decimal import Decimal

from app.schemas.common import AppBaseModel


class AlertScanRequest(AppBaseModel):
    """库存预警扫描请求，可按门店和 SKU 缩小扫描范围。"""

    store_code: str | None = None
    sku: Decimal | None = None


class AlertScanResponse(AppBaseModel):
    """库存预警扫描结果统计。"""

    success: bool
    scanned_count: int
    generated_count: int
    message: str


class AlertItem(AppBaseModel):
    """单条库存预警查询结果。"""

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
    """库存预警列表响应。"""

    items: list[AlertItem]
