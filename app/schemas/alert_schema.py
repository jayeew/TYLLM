from datetime import date

from pydantic import Field

from app.schemas.common import AppBaseModel


class AlertScanRequest(AppBaseModel):
    """库存预警扫描请求，可按机构编码、SKU 和计算日缩小范围。"""

    org_code: str | None = None
    sku: str | None = None
    calc_date: date | None = None
    limit: int | None = Field(default=None, ge=1)


class AlertScanResponse(AppBaseModel):
    """库存预警扫描结果统计。"""

    success: bool
    run_id: str
    scanned_count: int
    generated_count: int
    written_count: int
    message: str


class AlertListResponse(AppBaseModel):
    """库存预警结果列表响应。"""

    items: list[dict]
