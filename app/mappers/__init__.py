from app.mappers.ads_inventory_alert import AdsInventoryAlert
from app.mappers.ads_inventory_forecast import AdsInventoryForecast
from app.mappers.dim_base_info import DimBaseInfo
from app.mappers.fact_inventory_snapshot import FactInventorySnapshot
from app.mappers.fact_pos_transaction import FactPosTransaction

# 统一导出常用 ORM 映射类，方便其他模块按需集中导入。
__all__ = [
    "AdsInventoryAlert",
    "AdsInventoryForecast",
    "DimBaseInfo",
    "FactInventorySnapshot",
    "FactPosTransaction",
]
