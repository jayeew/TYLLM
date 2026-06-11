from fastapi import APIRouter, Depends, Query

from app.api.deps import verify_request
from app.config.database import ClickHouseClient, get_db
from app.schemas.product_schema import (
    DimProductListResponse,
    ProductStockListResponse,
)
from app.services.product_service import ProductService


router = APIRouter(dependencies=[Depends(verify_request)])


@router.get("/dim-product", response_model=DimProductListResponse)
def list_dim_products(
    product_code: str | None = None,
    international_barcode: str | None = None,
    limit: int | None = Query(default=None, ge=1),
    db: ClickHouseClient = Depends(get_db),
) -> DimProductListResponse:
    """查询商品档案源表记录。"""
    items = ProductService(db).list_dim_products(
        product_code=product_code,
        international_barcode=international_barcode,
        limit=limit,
    )
    return DimProductListResponse(items=items)


@router.get("/stock", response_model=ProductStockListResponse)
def list_product_stocks(
    org_code: str | None = None,
    product_code: str | None = None,
    international_barcode: str | None = None,
    limit: int | None = Query(default=None, ge=1),
    db: ClickHouseClient = Depends(get_db),
) -> ProductStockListResponse:
    """查询商品库存源表记录。"""
    items = ProductService(db).list_product_stocks(
        org_code=org_code,
        product_code=product_code,
        international_barcode=international_barcode,
        limit=limit,
    )
    return ProductStockListResponse(items=items)
