from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.core.forecast_rule import calculate_forecast
from app.core.indicator_calculator import (
    calc_avg_daily_sales_7d,
    calc_correction_factor,
    calc_dynamic_safety_stock,
    calc_effective_inventory,
    calc_purchase_cycle_days,
    calc_replenishment_in_transit,
    normalize_code,
    parse_replenishment_spec,
)
from app.repositories.base_info_repo import BaseInfoRepo, StoreMapping
from app.repositories.inventory_forecast_repo import InventoryForecastRepo
from app.repositories.inventory_snapshot_repo import InventorySnapshotRepo
from app.repositories.pos_transaction_repo import PosTransactionRepo


class ForecastService:
    """补货需求预测业务服务。"""

    def __init__(self, db: Session) -> None:
        """初始化本服务依赖的仓储对象。"""
        self.db = db
        self.snapshot_repo = InventorySnapshotRepo(db)
        self.pos_repo = PosTransactionRepo(db)
        self.forecast_repo = InventoryForecastRepo(db)
        self.base_info_repo = BaseInfoRepo(db)

    def _resolve_snapshot_store_code(self, store_code: str | None) -> Decimal | None:
        """把接口传入的门店条件转换为库存快照表使用的机构编码。"""
        if not store_code:
            return None

        try:
            # 如果调用方直接传机构编码，则可以直接用于库存表过滤。
            return Decimal(str(store_code))
        except (InvalidOperation, ValueError):
            # 如果调用方传的是门店编号，则通过基础信息表找到对应机构编码。
            return self.base_info_repo.get_org_code_by_store_code(store_code)

    def _resolve_result_store_code(
        self,
        input_store_code: str | None,
        snapshot_store_code: Decimal | None,
    ) -> str | None:
        """把清理结果表所需的门店条件统一成门店编号。"""
        if not input_store_code:
            return None
        if snapshot_store_code is None:
            return input_store_code
        return (
            self.base_info_repo.get_store_code_by_org_code(snapshot_store_code)
            or input_store_code
        )

    def _store_mapping(
        self,
        snapshot,
        mappings: dict[Decimal, StoreMapping],
    ) -> tuple[str, str]:
        """根据库存快照所属机构编码，解析 POS 门店编号和展示门店名称。"""
        mapping = mappings.get(snapshot.store_code)
        if mapping:
            return mapping.store_code, mapping.store_name
        normalized_store_code = normalize_code(snapshot.store_code)
        return normalized_store_code, snapshot.store_name

    def calculate_forecasts(
        self,
        store_code: str | None = None,
        sku: Decimal | None = None,
    ) -> dict:
        """计算补货需求预测，并把可计算的结果写入预测结果表。"""
        now = datetime.now().astimezone()
        now_ts = int(now.timestamp())
        # 建议补货日期按当天零点落库，便于按天聚合和查询。
        day_start = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)
        suggested_replenishment_date = int(day_start.timestamp())

        # 库存快照按机构编码过滤，结果表清理按门店编号过滤，两者需要分别解析。
        snapshot_store_code = self._resolve_snapshot_store_code(store_code)
        result_store_code = self._resolve_result_store_code(store_code, snapshot_store_code)

        if store_code and snapshot_store_code is None:
            # 传了门店条件但找不到机构编码时，直接返回空结果，避免误算全库。
            return {
                "success": True,
                "calculated_count": 0,
                "generated_count": 0,
                "skipped_count": 0,
                "message": "未找到对应机构编码，补货需求预测完成",
            }

        snapshots = self.snapshot_repo.list_inventory_snapshots(
            store_code=snapshot_store_code,
            sku=sku,
        )
        # 批量取映射，避免循环中反复查询基础信息表。
        mappings = self.base_info_repo.list_store_mappings_by_org_codes(
            sorted({snapshot.store_code for snapshot in snapshots})
        )

        generated_count = 0
        skipped_count = 0

        try:
            # Demo 场景下每次重算前先清理同范围旧结果，保证接口可重复验证。
            self.forecast_repo.clear_demo_forecasts(store_code=result_store_code, sku=sku)

            for snapshot in snapshots:
                pos_store_code, _ = self._store_mapping(snapshot, mappings)
                # POS 销量表使用门店编号，不使用库存表里的机构编码。
                total_sales_qty = self.pos_repo.sum_sales_qty_last_7_days(
                    store_code=pos_store_code,
                    sku=snapshot.sku,
                    now_ts=now_ts,
                )
                avg_daily_sales = calc_avg_daily_sales_7d(total_sales_qty)
                correction_factor, _ = calc_correction_factor(
                    snapshot=snapshot,
                    avg_daily_sales=avg_daily_sales,
                )
                # 动态安全库存需要销量波动，因此拉取近60天日销量序列。
                daily_sales_60d = self.pos_repo.list_daily_sales_qty(
                    store_code=pos_store_code,
                    sku=snapshot.sku,
                    now_ts=now_ts,
                    days=60,
                )
                daily_sales_30d = daily_sales_60d[-30:]

                # 组织补货公式所需的全部输入指标。
                effective_inventory = calc_effective_inventory(snapshot)
                in_transit_qty = calc_replenishment_in_transit(snapshot)
                purchase_cycle_days, _ = calc_purchase_cycle_days(snapshot)
                dynamic_safety_stock, _ = calc_dynamic_safety_stock(
                    base_safety_stock=snapshot.min_inventory_qty,
                    avg_daily_sales=avg_daily_sales,
                    daily_sales_30d=daily_sales_30d,
                    daily_sales_60d=daily_sales_60d,
                )
                replenishment_spec, _ = parse_replenishment_spec(snapshot)

                # 实际库存快照没有临期库存占比，无法执行“临期库存占比≥50%停止补货”规则。
                # 待补充批次效期和批次数量后，可把 near_expiry_ratio 传入 calculate_forecast。
                forecast_result = calculate_forecast(
                    avg_daily_sales=avg_daily_sales,
                    correction_factor=correction_factor,
                    purchase_cycle_days=purchase_cycle_days,
                    dynamic_safety_stock=dynamic_safety_stock,
                    effective_inventory=effective_inventory,
                    in_transit_qty=in_transit_qty,
                    replenishment_spec=replenishment_spec,
                )

                if not forecast_result:
                    # 当前库存和在途已覆盖需求时，不写预测结果。
                    continue

                if not forecast_result["can_calculate"]:
                    # 缺关键字段或应优先清库存时，不生成不可靠的补货建议。
                    skipped_count += 1
                    continue

                # 预计到货时间按建议补货日期 + 进货周期计算。
                estimated_arrival_time = int(
                    (
                        day_start
                        + timedelta(days=float(forecast_result["purchase_cycle_days"]))
                    ).timestamp()
                )
                self.forecast_repo.insert_forecast(
                    {
                        "store_code": pos_store_code,
                        "product_category": snapshot.product_category_name,
                        "product_name": snapshot.product_name,
                        "sku": snapshot.sku,
                        "product_brand": None,
                        "product_spec": snapshot.product_spec,
                        "suggested_replenishment_date": suggested_replenishment_date,
                        "suggested_qty": forecast_result["suggested_qty"],
                        "main_supplier_name": snapshot.supplier,
                        "supplier_code": None,
                        "warehouse": None,
                        "estimated_arrival_time": estimated_arrival_time,
                    }
                )
                generated_count += 1

            # 所有记录写入成功后统一提交，避免部分成功部分失败。
            self.db.commit()
        except Exception:
            # 任意一条处理失败时回滚本次计算产生的变更。
            self.db.rollback()
            raise

        # skipped_count 用于提示调用方有多少商品因字段不足或销量为0未生成建议。
        if skipped_count:
            message = (
                "补货需求预测完成；部分商品因缺少进货周期或近7天销量为0，未生成建议补货数量。"
            )
        else:
            message = "补货需求预测完成"

        return {
            "success": True,
            "calculated_count": len(snapshots),
            "generated_count": generated_count,
            "skipped_count": skipped_count,
            "message": message,
        }
