from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.repositories.base_info_repo import BaseInfoRepo
from app.repositories.inventory_alert_repo import InventoryAlertRepo
from app.repositories.inventory_forecast_repo import InventoryForecastRepo


class QueryService:
    """统一查询业务服务，封装结果表查询前的编码转换。"""

    def __init__(self, db: Session) -> None:
        """初始化查询所需的仓储对象。"""
        self.alert_repo = InventoryAlertRepo(db)
        self.forecast_repo = InventoryForecastRepo(db)
        self.base_info_repo = BaseInfoRepo(db)

    def _resolve_result_store_code(self, store_code: str | None) -> str | None:
        """把查询条件中的机构编码转换成结果表使用的门店编号。"""
        if not store_code:
            return None

        try:
            # 如果是纯数字，优先按机构编码理解，再尝试映射为门店编号。
            org_code = Decimal(str(store_code))
        except (InvalidOperation, ValueError):
            # 非数字一般就是门店编号，直接用于结果表查询。
            return store_code

        return self.base_info_repo.get_store_code_by_org_code(org_code) or store_code

    def list_alerts(
        self,
        store_code: str | None = None,
        sku: Decimal | None = None,
        warning_level: str | None = None,
        warning_category: str | None = None,
    ):
        """查询库存预警结果。"""
        result_store_code = self._resolve_result_store_code(store_code)
        return self.alert_repo.list_alerts(
            store_code=result_store_code,
            sku=sku,
            warning_level=warning_level,
            warning_category=warning_category,
        )

    def list_forecasts(
        self,
        store_code: str | None = None,
        sku: Decimal | None = None,
        product_category: str | None = None,
        warehouse: str | None = None,
    ):
        """查询补货预测结果。"""
        result_store_code = self._resolve_result_store_code(store_code)
        return self.forecast_repo.list_forecasts(
            store_code=result_store_code,
            sku=sku,
            product_category=product_category,
            warehouse=warehouse,
        )
