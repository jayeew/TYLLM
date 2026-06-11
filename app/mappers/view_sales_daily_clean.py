from app.mappers.base import ClickHouseMapper


class ViewSalesDailyClean(ClickHouseMapper):
    """view_sales_daily_clean 的显式列名映射。"""

    __tablename__ = "view_sales_daily_clean"
    alias = "v"
    columns = {
        "sale_date": "date",
        "sku": "sku_id",
        "product_name": "sku_name",
        "org_code": "store_id",
        "store_name": "store_name",
        "unit": "unit",
        "sales_qty": "sales",
        "avg_price": "avg_price",
        "sales_amount": "sales_amount",
        "trans_cnt": "trans_cnt",
        "cashier_cnt": "cashier_cnt",
    }
