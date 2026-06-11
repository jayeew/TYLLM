from app.schemas.common import AppBaseModel


class AlertScanRequest(AppBaseModel):
    """库存预警扫描请求，可按 view_sales_daily_clean 的机构编码和 SKU 缩小范围。"""

    org_code: str | None = None
    sku: str | None = None


class AlertScanResponse(AppBaseModel):
    """库存预警扫描占位结果统计。"""

    success: bool
    scanned_count: int
    generated_count: int
    message: str


class AlertListResponse(AppBaseModel):
    """库存预警占位列表响应。"""

    items: list[dict]
