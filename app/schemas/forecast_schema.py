from datetime import date

from pydantic import Field

from app.schemas.common import AppBaseModel


class ForecastCalculationRequest(AppBaseModel):
    """补货预测计算请求，可按机构编码、SKU 和计算日缩小范围。"""

    org_code: str | None = None
    sku: str | None = None
    calc_date: date | None = None
    limit: int | None = Field(default=None, ge=1)


class ForecastCalculationResponse(AppBaseModel):
    """补货预测计算结果统计。"""

    success: bool
    run_id: str
    calculated_count: int
    generated_count: int
    written_count: int
    skipped_count: int = 0
    message: str


class ForecastListResponse(AppBaseModel):
    """补货预测结果列表响应。"""

    items: list[dict]
