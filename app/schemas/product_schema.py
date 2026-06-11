from app.schemas.common import AppBaseModel


class DimProductListResponse(AppBaseModel):
    """商品档案原始记录列表响应。"""

    items: list[dict]


class ProductStockListResponse(AppBaseModel):
    """商品库存原始记录列表响应。"""

    items: list[dict]
