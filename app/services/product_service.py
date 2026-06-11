from app.config.database import ClickHouseClient
from app.repositories.dim_product_repo import DimProductRepo
from app.repositories.product_stock_repo import ProductStockRepo


class ProductService:
    """商品档案和库存源表查询服务。"""

    def __init__(self, db: ClickHouseClient) -> None:
        """初始化本服务依赖的仓储。"""
        self.dim_product_repo = DimProductRepo(db)
        self.product_stock_repo = ProductStockRepo(db)

    def list_dim_products(
        self,
        product_code: str | None = None,
        international_barcode: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """读取 dim_product 原始商品档案记录。"""
        return self.dim_product_repo.list_records(
            product_code=product_code,
            international_barcode=international_barcode,
            limit=limit,
        )

    def list_product_stocks(
        self,
        org_code: str | None = None,
        product_code: str | None = None,
        international_barcode: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """读取 dwd_product_stock 原始库存记录。"""
        return self.product_stock_repo.list_records(
            org_code=org_code,
            product_code=product_code,
            international_barcode=international_barcode,
            limit=limit,
        )
