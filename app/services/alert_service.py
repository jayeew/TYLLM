from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.core.alert_rule import judge_alerts
from app.core.indicator_calculator import (
    DEFAULT_SAFETY_BUFFER_DAYS,
    calc_avg_daily_sales_7d,
    calc_correction_factor,
    calc_coverage_days,
    calc_effective_inventory,
    calc_purchase_cycle_days,
    normalize_code,
)
from app.repositories.base_info_repo import BaseInfoRepo, StoreMapping
from app.repositories.inventory_alert_repo import InventoryAlertRepo
from app.repositories.inventory_snapshot_repo import InventorySnapshotRepo
from app.repositories.pos_transaction_repo import PosTransactionRepo


TWO_DECIMAL = Decimal("0.01")


def format_decimal(value: Decimal | None) -> str:
    """把 Decimal 格式化成两位小数；无法计算的指标直接显示说明。"""
    if value is None:
        return "无法计算"
    return str(value.quantize(TWO_DECIMAL, rounding=ROUND_HALF_UP))


class AlertService:
    """库存预警扫描业务服务。"""

    def __init__(self, db: Session) -> None:
        """初始化本服务依赖的仓储对象。"""
        self.db = db
        self.snapshot_repo = InventorySnapshotRepo(db)
        self.pos_repo = PosTransactionRepo(db)
        self.alert_repo = InventoryAlertRepo(db)
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

    def scan_alerts(
        self,
        store_code: str | None = None,
        sku: Decimal | None = None,
    ) -> dict:
        """扫描库存快照并生成库存预警结果。"""
        now_ts = int(datetime.now().timestamp())
        # 库存快照按机构编码过滤，结果表清理按门店编号过滤，两者需要分别解析。
        snapshot_store_code = self._resolve_snapshot_store_code(store_code)
        result_store_code = self._resolve_result_store_code(store_code, snapshot_store_code)

        if store_code and snapshot_store_code is None:
            # 传了门店条件但找不到机构编码时，直接返回空结果，避免误扫全库。
            return {
                "success": True,
                "scanned_count": 0,
                "generated_count": 0,
                "message": "未找到对应机构编码，库存预警扫描完成",
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
        unavailable_rule_count = 0

        try:
            # Demo 场景下每次重算前先清理同范围旧结果，保证接口可重复验证。
            self.alert_repo.clear_demo_alerts(store_code=result_store_code, sku=sku)

            for snapshot in snapshots:
                pos_store_code, warning_store = self._store_mapping(snapshot, mappings)
                # POS 销量表使用门店编号，不使用库存表里的机构编码。
                total_sales_qty = self.pos_repo.sum_sales_qty_last_7_days(
                    store_code=pos_store_code,
                    sku=snapshot.sku,
                    now_ts=now_ts,
                )

                # 先计算规则需要的基础指标，再交给纯规则函数判断等级。
                avg_daily_sales = calc_avg_daily_sales_7d(total_sales_qty)
                correction_factor, factor_notes = calc_correction_factor(
                    snapshot=snapshot,
                    avg_daily_sales=avg_daily_sales,
                )
                coverage_days = calc_coverage_days(
                    current_qty=snapshot.inventory_qty,
                    avg_daily_sales=avg_daily_sales,
                    correction_factor=correction_factor,
                )
                effective_inventory = calc_effective_inventory(snapshot)
                purchase_cycle_days, purchase_cycle_notes = calc_purchase_cycle_days(snapshot)

                # 实际库存快照没有批次效期、保质期、临期批次数量和过期批次数量。
                # 临期/过期预警暂无法计算，字段补齐后传入 near_expiry_ratio/expired_qty 即可启用规则。
                unavailable_notes = [
                    *purchase_cycle_notes,
                    "无法计算临期/过期预警：实际库存快照缺少批次效期、保质期、临期批次数量和过期批次数量。",
                ]
                unavailable_rule_count += len(unavailable_notes)

                alert_results = judge_alerts(
                    avg_daily_sales=avg_daily_sales,
                    coverage_days=coverage_days,
                    effective_inventory=effective_inventory,
                    purchase_cycle_days=purchase_cycle_days,
                    safety_buffer_days=DEFAULT_SAFETY_BUFFER_DAYS,
                )

                if not alert_results:
                    # 无任何预警命中时不写结果表。
                    continue

                # 预警详情中同时放入指标值和不可计算说明，便于前端/运营追溯。
                note_text = "；".join([*factor_notes, *unavailable_notes])
                warning_detail_prefix = (
                    f"门店：{pos_store_code}，SKU：{normalize_code(snapshot.sku)}，"
                    f"商品：{snapshot.product_name}，"
                    f"库存数量：{format_decimal(snapshot.inventory_qty)}，"
                    f"有效库存：{format_decimal(effective_inventory)}，"
                    f"近7天日均销量：{format_decimal(avg_daily_sales)}，"
                    f"修正因子K：{format_decimal(correction_factor)}，"
                    f"预计销售时长T：{format_decimal(coverage_days)}天"
                )

                for alert_result in alert_results:
                    replenishment_suggestion = None
                    if alert_result["category"] == "补货预警":
                        # 补货建议依赖进货周期；缺字段时只给出补字段说明，不生成伪建议。
                        if purchase_cycle_days is None:
                            replenishment_suggestion = (
                                "缺少进货周期，暂无法计算建议补货数量；请补充配送周期/送货天数或近6个月进货明细。"
                            )
                        else:
                            replenishment_suggestion = "建议触发补货预测"

                    warning_detail = (
                        f"{warning_detail_prefix}，预警原因：{alert_result['reason']}"
                    )
                    if note_text:
                        warning_detail = f"{warning_detail}。计算说明：{note_text}"

                    # 每个预警类别单独写一条记录，便于后续待办或推送按类别分发。
                    self.alert_repo.insert_alert(
                        {
                            "store_code": pos_store_code,
                            "sku": snapshot.sku,
                            "product_name": snapshot.product_name,
                            "warning_category": alert_result["category"],
                            "warning_time": now_ts,
                            "warning_store": warning_store,
                            "warning_product_category": snapshot.product_category_name,
                            "warning_level": alert_result["level"],
                            "warning_detail": warning_detail,
                            "replenishment_suggestion": replenishment_suggestion,
                        }
                    )
                    generated_count += 1

            # 所有记录写入成功后统一提交，避免部分成功部分失败。
            self.db.commit()
        except Exception:
            # 任意一条处理失败时回滚本次扫描产生的变更。
            self.db.rollback()
            raise

        return {
            "success": True,
            "scanned_count": len(snapshots),
            "generated_count": generated_count,
            "message": (
                "库存预警扫描完成；进货周期类T阈值、临期/过期等缺字段规则已在详情中说明。"
                if unavailable_rule_count
                else "库存预警扫描完成"
            ),
        }
