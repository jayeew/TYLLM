from app.schemas.common import AppBaseModel


class ForecastCalculationRequest(AppBaseModel):
    """补货预测计算请求，可按 view_sales_daily_clean 的机构编码和 SKU 缩小范围。"""

    org_code: str | None = None
    sku: str | None = None


class ForecastCalculationResponse(AppBaseModel):
    """补货预测计算占位结果统计。"""

    success: bool
    calculated_count: int
    generated_count: int
    skipped_count: int = 0
    message: str


class ForecastListResponse(AppBaseModel):
    """补货预测占位列表响应。"""

    items: list[dict]
