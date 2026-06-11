from app.config.config import settings
from app.config.database import ClickHouseClient
from app.sources.clickhouse import ClickHouseSourceRepo


class ProductService:
    """商品档案和库存源表查询服务。"""

    def __init__(self, db: ClickHouseClient) -> None:
        """初始化本服务依赖的 ClickHouse 源表仓储。"""
        self.source_repo = ClickHouseSourceRepo(settings, client=db)

    def list_dim_products(
        self,
        product_code: str | None = None,
        international_barcode: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """读取 dim_product 原始商品档案记录。"""
        return self.source_repo.list_dim_product_records(
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
        return self.source_repo.list_product_stock_records(
            org_code=org_code,
            product_code=product_code,
            international_barcode=international_barcode,
            limit=limit,
        )
