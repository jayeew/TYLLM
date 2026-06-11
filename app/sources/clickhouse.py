"""ClickHouse 数据访问层。

这个文件只负责和 ClickHouse 打交道：
- 连接 ClickHouse。
- 按 mapper 中的字段映射拼 SELECT SQL。
- 读取三张源表/视图：销售日视图、商品档案表、库存表。
- 读取预警/补货计算所需的聚合输入。
- 自动创建结果表。
- 写入预警/补货结果。
- 查询预警/补货结果。

注意：这里不写业务公式。预警和补货公式在 app/core/ 中。
"""

# 允许在类型标注里使用尚未运行时求值的类型，减少循环引用/兼容性问题。
from __future__ import annotations

# date 用于 ClickHouse Date 参数，例如 calc_date。
from datetime import date
# Any 用于标注 clickhouse_connect client 这种外部库对象。
from typing import Any

# Settings 是项目统一配置对象的类型，里面包含 ClickHouse 连接、表名、默认 limit 等配置。
from app.config.config import Settings
# ensure_clickhouse_no_proxy 会把 ClickHouse 内网地址加入 NO_PROXY，避免请求被代理劫持。
from app.config.database import ensure_clickhouse_no_proxy
# DimProduct 是 dim_product 商品档案表的“代码字段名 -> 物理列名”映射。
from app.mappers.dim_product import DimProduct
# DwdProductStock 是 dwd_product_stock 库存表的“代码字段名 -> 物理列名”映射。
from app.mappers.dwd_product_stock import DwdProductStock
# ViewSalesDailyClean 是 view_sales_daily_clean 销售日视图的“代码字段名 -> 物理列名”映射。
from app.mappers.view_sales_daily_clean import ViewSalesDailyClean
# 结果表建表 SQL 常量，服务启动/写入前会用它们确保结果表存在。
from app.sources.result_table_sql import (
    CREATE_ALERT_RESULT_TABLE_SQL,
    CREATE_FORECAST_RESULT_TABLE_SQL,
)


# 预警结果写入 ClickHouse 时的列顺序。
# ClickHouse insert 是按列名和数据顺序写入的，所以这里必须和结果 dict 的 key 对齐。
ALERT_RESULT_INSERT_COLUMNS = [
    "run_id",  # 本次预警计算批次 ID。
    "calc_date",  # 业务计算日。
    "org_code",  # 机构编码。
    "org_name",  # 机构名称。
    "product_code",  # 商品编码/SKU。
    "product_name",  # 商品名称。
    "product_category_code",  # 商品类别编码。
    "product_category_name",  # 商品类别名称。
    "unit",  # 商品单位。
    "inventory_qty",  # 当前库存数量。
    "available_inventory_qty",  # 可用库存数量，初版等于当前库存。
    "effective_inventory_qty",  # 有效库存数量，初版等于当前库存。
    "sales_avg_7",  # 近 7 天日均销量。
    "sales_avg_15",  # 近 15 天日均销量。
    "sales_avg_30",  # 近 30 天日均销量。
    "base_daily_sales",  # 按 7/15/30 天回退后的基础日销量。
    "correction_factor",  # 综合修正因子。
    "corrected_daily_demand",  # 修正后日需求。
    "coverage_days",  # 库存覆盖天数。
    "estimated_sale_days",  # 预计销售时长。
    "warning_risk_days",  # 预警风险天数。
    "safety_stock_qty",  # 安全库存阈值。
    "safety_stock_gap",  # 安全库存缺口。
    "expired_stock_qty",  # 过期库存数量。
    "expiring_stock_qty",  # 临期库存数量。
    "expiring_stock_ratio",  # 临期库存占比。
    "alert_status",  # 预警状态。
    "alert_type",  # 预警类型。
    "warning_level",  # 预警等级。
    "warning_level_name",  # 预警等级名称。
    "reason",  # 触发原因/说明。
    "missing_fields",  # 当前计算缺失的字段清单。
]

# 补货结果写入 ClickHouse 时的列顺序。
# 这里不包含 created_at，因为结果表用 DEFAULT now() 自动生成写入时间。
FORECAST_RESULT_INSERT_COLUMNS = [
    "run_id",  # 本次补货预测批次 ID。
    "calc_date",  # 业务计算日。
    "org_code",  # 机构编码。
    "org_name",  # 机构名称。
    "product_code",  # 商品编码/SKU。
    "product_name",  # 商品名称。
    "product_category_code",  # 商品类别编码。
    "product_category_name",  # 商品类别名称。
    "supplier_name",  # 供应商名称。
    "unit",  # 商品单位。
    "inventory_qty",  # 当前库存数量。
    "effective_inventory_qty",  # 有效库存数量。
    "in_transit_qty",  # 计入补货计算的在途库存。
    "sales_avg_7",  # 近 7 天日均销量。
    "sales_avg_15",  # 近 15 天日均销量。
    "sales_avg_30",  # 近 30 天日均销量。
    "base_daily_sales",  # 基础日销量。
    "correction_factor",  # 综合修正因子。
    "corrected_daily_demand",  # 修正后日需求。
    "purchase_cycle_days",  # 进货周期天数。
    "replenish_cycle_demand",  # 补货周期需求。
    "safety_stock_mode",  # 安全库存计算模式。
    "safety_stock_qty",  # 安全库存数量。
    "gap_qty",  # 补货缺口。
    "raw_replenish_qty",  # 原始建议补货数量。
    "min_order_qty",  # 最小订货量。
    "pack_qty",  # 箱规/包装规格。
    "system_replenish_qty",  # 系统测算补货数量。
    "manual_replenish_qty",  # 人工调整补货数量。
    "final_replenish_qty",  # 最终建议补货数量。
    "replenish_after_days",  # 建议补货等待天数。
    "suggested_replenish_date",  # 建议补货日期。
    "expected_arrival_date",  # 预计到货日期。
    "stop_replenishment_reason",  # 停止补货原因。
    "missing_fields",  # 当前计算缺失的字段清单。
]

# 查询预警结果时需要把 created_at 也查出来，方便用户知道结果是什么时候写入的。
ALERT_RESULT_SELECT_COLUMNS = [*ALERT_RESULT_INSERT_COLUMNS, "created_at"]
# 查询补货结果时也附带 created_at。
FORECAST_RESULT_SELECT_COLUMNS = [*FORECAST_RESULT_INSERT_COLUMNS, "created_at"]


class ClickHouseSchemaError(RuntimeError):
    """ClickHouse 源对象字段无法满足读取输入时抛出。"""


class ClickHouseSourceRepo:
    """ClickHouse 源数据/结果数据仓储。

    这个类是 app 里所有 ClickHouse 读写操作的集中入口。
    服务层调用它，不直接拼 SQL。
    """

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        """保存配置和可选外部传入的 ClickHouse client。

        settings:
            项目配置，包含连接信息、表名、默认 limit 等。
        client:
            FastAPI 依赖注入传进来的共享 ClickHouse client。
            测试或脚本里也可以传一个现成 client。
        """
        # 保存配置对象，后续所有表名、连接参数、limit 都从这里取。
        self.settings = settings
        # 保存 ClickHouse client；如果调用方没传，后面 client 属性会延迟创建。
        self._client: Any | None = client

    @property
    def client(self) -> Any:
        """返回 ClickHouse client；没有就现场创建。

        这里用“延迟创建”，是为了避免 import 这个类时就立刻连接数据库。
        """
        # 如果外部已经传入 client，就不会进入这个分支。
        if self._client is None:
            # 确保访问 ClickHouse 内网地址时不走 HTTP 代理。
            ensure_clickhouse_no_proxy(self.settings.clickhouse_host)
            try:
                # clickhouse_connect 是真正连接 ClickHouse 的第三方库。
                import clickhouse_connect
            except ImportError as exc:
                # 依赖没装时给出明确提示，而不是让用户面对 obscure import error。
                raise RuntimeError(
                    "当前项目固定使用 ClickHouse，请先安装依赖：pip install -r requirements.txt"
                ) from exc

            # 根据 .env / Settings 创建 ClickHouse HTTP client。
            self._client = clickhouse_connect.get_client(
                host=self.settings.clickhouse_host,  # ClickHouse 主机地址。
                port=self.settings.clickhouse_port,  # ClickHouse HTTP 端口，通常是 8123。
                username=self.settings.clickhouse_user,  # 登录用户名。
                password=self.settings.clickhouse_password,  # 登录密码。
                database=self.settings.clickhouse_database,  # 默认数据库。
                secure=self.settings.clickhouse_secure,  # 是否使用 HTTPS。
                connect_timeout=self.settings.clickhouse_connect_timeout,  # 连接超时秒数。
                send_receive_timeout=self.settings.clickhouse_send_receive_timeout,  # 读写超时秒数。
            )
        # 返回已创建或外部传入的 client。
        return self._client

    def list_sales_daily_records(
        self,
        org_code: str | None = None,
        sku: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """读取 view_sales_daily_clean 原始日销售记录，不附加业务计算。"""
        # where_parts 用来收集可选过滤条件，比如机构、SKU。
        where_parts: list[str] = []
        # params 是 ClickHouse 参数绑定字典，避免把用户输入直接拼进 SQL。
        params: dict[str, Any] = {
            # 如果调用方没传 limit，就用配置里的默认销售视图查询上限。
            "limit": limit or self.settings.clickhouse_sales_daily_query_limit,
        }

        # 如果传了机构编码，就增加机构过滤。
        if org_code:
            # toString(...) 是为了兼容 ClickHouse 字段可能不是 String 的情况。
            where_parts.append(
                f"toString({self._sales_expr('org_code')}) = {{org_code:String}}"
            )
            # 把机构编码放入参数字典，由 ClickHouse client 绑定。
            params["org_code"] = org_code
        # 如果传了 SKU，就增加 SKU 过滤。
        if sku:
            # 使用 mapper 表达式，避免在这里写死物理列名。
            where_parts.append(f"toString({self._sales_expr('sku')}) = {{sku:String}}")
            # 把 SKU 放入参数字典。
            params["sku"] = sku

        # 如果有过滤条件，就拼 WHERE；没有就不拼 WHERE。
        where_clause = f"WHERE {' AND '.join(where_parts)} " if where_parts else ""
        # 拼完整查询 SQL。
        query = (
            # SELECT 后面的字段来自 ViewSalesDailyClean.columns。
            f"SELECT {self._sales_select_clause()} "
            # FROM 使用配置里的销售视图表名，并给它起别名 v。
            f"FROM {self._sales_daily_table()} AS v "
            # 这里插入可选 WHERE。
            f"{where_clause}"
            # 默认按日期倒序，再按机构、SKU 排序，方便看最近记录。
            f"ORDER BY {self._sales_expr('sale_date')} DESC, "
            f"{self._sales_expr('org_code')}, {self._sales_expr('sku')} "
            # limit 使用参数绑定。
            "LIMIT {limit:UInt64}"
        )
        # 执行 SQL，并把 ClickHouse 返回值转成 list[dict]。
        return self._query_dicts(query, params)

    def list_dim_product_records(
        self,
        product_code: str | None = None,
        international_barcode: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """读取 dim_product 原始商品档案记录，不附加业务计算。"""
        # 收集商品档案查询的可选 WHERE 条件。
        where_parts: list[str] = []
        # 查询参数；limit 不传时使用商品档案默认查询上限。
        params: dict[str, Any] = {
            "limit": limit or self.settings.clickhouse_dim_product_query_limit,
        }

        # 如果传了商品编码，就按商品编码过滤。
        if product_code:
            # _product_expr('product_code') 会映射到真实字段，比如 p.`sku_id`。
            where_parts.append(
                f"toString({self._product_expr('product_code')}) = {{product_code:String}}"
            )
            # 绑定商品编码参数。
            params["product_code"] = product_code
        # 如果传了国际条码，就按条码过滤。
        if international_barcode:
            # 这里拆成多段字符串只是为了避免单行太长。
            where_parts.append(
                "toString("
                f"{self._product_expr('international_barcode')}"
                ") = {international_barcode:String}"
            )
            # 绑定国际条码参数。
            params["international_barcode"] = international_barcode

        # 有过滤条件就生成 WHERE，没有过滤条件就查默认前 N 条。
        where_clause = f"WHERE {' AND '.join(where_parts)} " if where_parts else ""
        # 拼商品档案查询 SQL。
        query = (
            # SELECT 字段来自 DimProduct.columns。
            f"SELECT {self._product_select_clause()} "
            # FROM 使用配置里的商品档案表名，并给它起别名 p。
            f"FROM {self._dim_product_table()} AS p "
            # 可选 WHERE。
            f"{where_clause}"
            # 按商品编码排序。
            f"ORDER BY {self._product_expr('product_code')} "
            # limit 使用参数绑定。
            "LIMIT {limit:UInt64}"
        )
        # 执行并返回字典列表。
        return self._query_dicts(query, params)

    def list_product_stock_records(
        self,
        org_code: str | None = None,
        product_code: str | None = None,
        international_barcode: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """读取 dwd_product_stock 原始库存记录，不附加业务计算。"""
        # 收集库存表查询的可选 WHERE 条件。
        where_parts: list[str] = []
        # 查询参数；limit 不传时使用库存表默认查询上限。
        params: dict[str, Any] = {
            "limit": limit or self.settings.clickhouse_product_stock_query_limit,
        }

        # 如果传了机构编码，就按机构过滤。
        if org_code:
            # 机构编码按字符串比较，避免前导零或类型差异问题。
            where_parts.append(
                f"toString({self._stock_expr('org_code')}) = {{org_code:String}}"
            )
            # 绑定机构参数。
            params["org_code"] = org_code
        # 如果传了商品编码，就按商品过滤。
        if product_code:
            # _stock_expr 会把代码字段名 product_code 转成 s.`product_code`。
            where_parts.append(
                f"toString({self._stock_expr('product_code')}) = {{product_code:String}}"
            )
            # 绑定商品编码参数。
            params["product_code"] = product_code
        # 如果传了国际条码，就按条码过滤。
        if international_barcode:
            # 拆成多段字符串，保持格式可读。
            where_parts.append(
                "toString("
                f"{self._stock_expr('international_barcode')}"
                ") = {international_barcode:String}"
            )
            # 绑定国际条码参数。
            params["international_barcode"] = international_barcode

        # 生成可选 WHERE。
        where_clause = f"WHERE {' AND '.join(where_parts)} " if where_parts else ""
        # 拼库存表查询 SQL。
        query = (
            # SELECT 字段来自 DwdProductStock.columns。
            f"SELECT {self._stock_select_clause()} "
            # FROM 使用库存表名，并给它起别名 s。
            f"FROM {self._product_stock_table()} AS s "
            # 可选 WHERE。
            f"{where_clause}"
            # 按机构、商品排序。
            f"ORDER BY {self._stock_expr('org_code')}, {self._stock_expr('product_code')} "
            # limit 使用参数绑定。
            "LIMIT {limit:UInt64}"
        )
        # 执行并返回字典列表。
        return self._query_dicts(query, params)

    def list_inventory_calculation_inputs(
        self,
        calc_date: date,
        org_code: str | None = None,
        product_code: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """以库存表为主驱动读取预警和补货计算输入。

        这是预警和补货最重要的输入查询：
        - 主表是 dwd_product_stock，因为预警/补货要覆盖有库存的门店商品。
        - 左关联 dim_product，补商品档案信息。
        - 左关联销售聚合子查询，补最近 7/15/30 天日均销量。
        """
        # 收集库存主表上的可选过滤条件。
        where_parts: list[str] = []
        # 参数字典：calc_date 用于最近 N 天销量窗口，limit 控制处理数量。
        params: dict[str, Any] = {
            "calc_date": calc_date,
            "limit": limit or self.settings.clickhouse_product_stock_query_limit,
        }

        # 如果指定机构，只处理该机构库存行。
        if org_code:
            # 使用 toString 做稳健比较。
            where_parts.append(
                f"toString({self._stock_expr('org_code')}) = {{org_code:String}}"
            )
            # 绑定机构编码。
            params["org_code"] = org_code
        # 如果指定商品，只处理该商品库存行。
        if product_code:
            # 使用 mapper 表达式，不直接写 s.product_code。
            where_parts.append(
                f"toString({self._stock_expr('product_code')}) = {{product_code:String}}"
            )
            # 绑定商品编码。
            params["product_code"] = product_code

        # 把可选过滤条件拼成 WHERE 片段。
        where_clause = f"WHERE {' AND '.join(where_parts)} " if where_parts else ""
        # 销售日期字段表达式，例如 v.`date`。
        sales_date = self._sales_expr("sale_date")
        # 销售数量字段表达式，例如 v.`sales`。
        sales_qty = self._sales_expr("sales_qty")
        # 销售视图里的机构字段表达式，例如 v.`store_id`。
        sales_org = self._sales_expr("org_code")
        # 销售视图里的商品字段表达式，例如 v.`sku_id`。
        sales_sku = self._sales_expr("sku")

        # 这个子查询按“门店 + 商品”聚合最近 7/15/30 天日均销量。
        sales_subquery = (
            # 子查询 SELECT 开始。
            "SELECT "
            # 输出机构编码，统一转 String，方便和库存表 JOIN。
            f"toString({sales_org}) AS org_code, "
            # 输出商品编码，统一转 String。
            f"toString({sales_sku}) AS product_code, "
            # 计算最近 7 天销量合计 / 7，并 cast 成 Decimal(18, 4)。
            "CAST(round(ifNull(sumIf(toFloat64("
            f"{sales_qty}), {sales_date} >= addDays({{calc_date:Date}}, -7)"
            " AND "
            f"{sales_date} < {{calc_date:Date}}), 0) / 7, 4), 'Decimal(18, 4)') "
            # 7 天日均销量别名。
            "AS sales_avg_7, "
            # 计算最近 15 天销量合计 / 15。
            "CAST(round(ifNull(sumIf(toFloat64("
            f"{sales_qty}), {sales_date} >= addDays({{calc_date:Date}}, -15)"
            " AND "
            f"{sales_date} < {{calc_date:Date}}), 0) / 15, 4), 'Decimal(18, 4)') "
            # 15 天日均销量别名。
            "AS sales_avg_15, "
            # 计算最近 30 天销量合计 / 30。
            "CAST(round(ifNull(sumIf(toFloat64("
            f"{sales_qty}), {sales_date} >= addDays({{calc_date:Date}}, -30)"
            " AND "
            f"{sales_date} < {{calc_date:Date}}), 0) / 30, 4), 'Decimal(18, 4)') "
            # 30 天日均销量别名。
            "AS sales_avg_30 "
            # 从销售日视图读取，别名 v。
            f"FROM {self._sales_daily_table()} AS v "
            # 为了减少扫描量，只查 calc_date 前 30 天。
            f"WHERE {sales_date} >= addDays({{calc_date:Date}}, -30) "
            # 销售窗口不包含 calc_date 当天。
            f"AND {sales_date} < {{calc_date:Date}} "
            # 按门店和商品聚合。
            f"GROUP BY toString({sales_org}), toString({sales_sku})"
        )

        # 主查询：库存表 + 商品档案 + 销售聚合。
        query = (
            # 主 SELECT 开始。
            "SELECT "
            # 机构编码来自库存表。
            f"{self._stock_expr('org_code')} AS org_code, "
            # 机构名称来自库存表。
            f"{self._stock_expr('org_name')} AS org_name, "
            # 商品编码来自库存表。
            f"{self._stock_expr('product_code')} AS product_code, "
            # 国际条码来自库存表。
            f"{self._stock_expr('international_barcode')} AS international_barcode, "
            # 商品类别编码来自库存表。
            f"{self._stock_expr('product_category_code')} AS product_category_code, "
            # 商品类别名称来自库存表。
            f"{self._stock_expr('product_category_name')} AS product_category_name, "
            # 供应商名称来自库存表。
            f"{self._stock_expr('supplier_name')} AS supplier_name, "
            # 单位来自库存表。
            f"{self._stock_expr('unit')} AS unit, "
            # 商品名称来自库存表。
            f"{self._stock_expr('product_name')} AS product_name, "
            # 商品状态来自库存表。
            f"{self._stock_expr('product_status')} AS product_status, "
            # 当前库存数量来自库存表。
            f"{self._stock_expr('inventory_qty')} AS inventory_qty, "
            # 大包装/箱规数量来自库存表。
            f"{self._stock_expr('large_package_qty')} AS large_package_qty, "
            # 采购在途数量来自库存表。
            f"{self._stock_expr('purchase_in_transit_qty')} AS purchase_in_transit_qty, "
            # 销售在途数量来自库存表，初版补货不计入，但结果输入保留。
            f"{self._stock_expr('sales_in_transit_qty')} AS sales_in_transit_qty, "
            # 要货在途数量来自库存表。
            f"{self._stock_expr('requisition_in_transit_qty')} AS requisition_in_transit_qty, "
            # 调拨在途数量来自库存表，初版补货不计入，但结果输入保留。
            f"{self._stock_expr('transfer_in_transit_qty')} AS transfer_in_transit_qty, "
            # 配送在途数量来自库存表。
            f"{self._stock_expr('distribution_in_transit_qty')} AS distribution_in_transit_qty, "
            # 配退在途数量来自库存表，初版补货不计入。
            f"{self._stock_expr('distribution_out_transit_qty')} AS distribution_out_transit_qty, "
            # 最小库存量，用于预警安全库存阈值。
            f"{self._stock_expr('min_inventory_qty')} AS min_inventory_qty, "
            # 最大库存量，当前结果暂未使用，但作为输入保留。
            f"{self._stock_expr('max_inventory_qty')} AS max_inventory_qty, "
            # 商品建档日期来自商品档案表。
            f"{self._product_expr('product_created_at')} AS product_created_at, "
            # 采购因子来自商品档案表，可作为包装规格 fallback。
            f"{self._product_expr('purchase_factor')} AS purchase_factor, "
            # 商品档案中的类别编码。
            f"{self._product_expr('category_code')} AS dim_category_code, "
            # 商品档案中的类别名称。
            f"{self._product_expr('product_category')} AS dim_product_category, "
            # 保质期天数，当前缺少批次日期，暂未用于临期计算。
            f"{self._product_expr('shelf_life_days')} AS shelf_life_days, "
            # 如果销售子查询没有匹配记录，7 天日均销量补 0。
            f"ifNull(sa.sales_avg_7, CAST(0, 'Decimal(18, 4)')) AS sales_avg_7, "
            # 如果销售子查询没有匹配记录，15 天日均销量补 0。
            f"ifNull(sa.sales_avg_15, CAST(0, 'Decimal(18, 4)')) AS sales_avg_15, "
            # 如果销售子查询没有匹配记录，30 天日均销量补 0。
            f"ifNull(sa.sales_avg_30, CAST(0, 'Decimal(18, 4)')) AS sales_avg_30 "
            # 主表是库存表，别名 s。
            f"FROM {self._product_stock_table()} AS s "
            # 用 ANY LEFT JOIN 连接商品档案；ANY 可避免商品档案重复行造成库存行膨胀。
            f"ANY LEFT JOIN {self._dim_product_table()} AS p "
            # 商品档案商品编码 = 库存商品编码。
            f"ON toString({self._product_expr('product_code')}) = "
            f"toString({self._stock_expr('product_code')}) "
            # 左连接销售聚合子查询。
            f"LEFT JOIN ({sales_subquery}) AS sa "
            # 销售聚合机构 = 库存机构。
            f"ON sa.org_code = toString({self._stock_expr('org_code')}) "
            # 销售聚合商品 = 库存商品。
            f"AND sa.product_code = toString({self._stock_expr('product_code')}) "
            # 插入可选过滤条件。
            f"{where_clause}"
            # 保证结果顺序稳定。
            f"ORDER BY {self._stock_expr('org_code')}, {self._stock_expr('product_code')} "
            # 限制本次最多处理多少库存行。
            "LIMIT {limit:UInt64}"
        )
        # 执行主查询，返回预警/补货计算输入列表。
        return self._query_dicts(query, params)

    def ensure_result_tables(self) -> None:
        """确保预警和补货结果表存在。"""
        # 创建预警结果表；format 只替换已 quote 的表名。
        self.client.command(
            CREATE_ALERT_RESULT_TABLE_SQL.format(
                alert_result_table=self._alert_result_table()
            )
        )
        # 创建补货结果表；如果已经存在，ClickHouse 不会重复创建。
        self.client.command(
            CREATE_FORECAST_RESULT_TABLE_SQL.format(
                forecast_result_table=self._forecast_result_table()
            )
        )

    def insert_alert_results(self, rows: list[dict[str, Any]]) -> int:
        """批量写入库存预警结果快照。"""
        # 复用通用插入函数，传入预警结果表名和预警列清单。
        return self._insert_rows(
            table_name=self.settings.clickhouse_alert_result_table,
            columns=ALERT_RESULT_INSERT_COLUMNS,
            rows=rows,
        )

    def insert_forecast_results(self, rows: list[dict[str, Any]]) -> int:
        """批量写入补货预测结果快照。"""
        # 复用通用插入函数，传入补货结果表名和补货列清单。
        return self._insert_rows(
            table_name=self.settings.clickhouse_forecast_result_table,
            columns=FORECAST_RESULT_INSERT_COLUMNS,
            rows=rows,
        )

    def list_alert_results(
        self,
        run_id: str | None = None,
        calc_date: date | None = None,
        org_code: str | None = None,
        product_code: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """查询库存预警结果快照。"""
        # 复用通用结果查询函数，只换表名和列清单。
        return self._list_result_records(
            table_name=self._alert_result_table(),
            columns=ALERT_RESULT_SELECT_COLUMNS,
            run_id=run_id,
            calc_date=calc_date,
            org_code=org_code,
            product_code=product_code,
            limit=limit,
        )

    def list_forecast_results(
        self,
        run_id: str | None = None,
        calc_date: date | None = None,
        org_code: str | None = None,
        product_code: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """查询补货预测结果快照。"""
        # 复用通用结果查询函数，只换表名和列清单。
        return self._list_result_records(
            table_name=self._forecast_result_table(),
            columns=FORECAST_RESULT_SELECT_COLUMNS,
            run_id=run_id,
            calc_date=calc_date,
            org_code=org_code,
            product_code=product_code,
            limit=limit,
        )

    def _insert_rows(
        self,
        table_name: str,
        columns: list[str],
        rows: list[dict[str, Any]],
    ) -> int:
        """按指定列顺序批量插入结果行。"""
        # 没有结果行时直接返回 0，避免 ClickHouse 空插入。
        if not rows:
            return 0
        # 把 list[dict] 转成 clickhouse_connect 需要的二维数组。
        data = [
            # 每一行都严格按 columns 中的列顺序取值。
            [row.get(column_name) for column_name in columns]
            # 遍历全部待插入结果行。
            for row in rows
        ]
        # 执行 ClickHouse insert；column_names 明确告诉 ClickHouse 每列对应什么字段。
        self.client.insert(table_name, data, column_names=columns)
        # 返回实际写入行数。
        return len(data)

    def _list_result_records(
        self,
        table_name: str,
        columns: list[str],
        run_id: str | None,
        calc_date: date | None,
        org_code: str | None,
        product_code: str | None,
        limit: int | None,
    ) -> list[dict[str, Any]]:
        """通用结果表查询函数。"""
        # 收集可选过滤条件。
        where_parts: list[str] = []
        # 查询参数；limit 不传时用结果查询默认上限。
        params: dict[str, Any] = {
            "limit": limit or self.settings.clickhouse_result_query_limit,
        }

        # 如果传 run_id，就只查某一次运行批次。
        if run_id:
            where_parts.append("toString(`run_id`) = {run_id:String}")
            params["run_id"] = run_id
        # 如果传 calc_date，就只查某个业务计算日。
        if calc_date:
            where_parts.append("`calc_date` = {calc_date:Date}")
            params["calc_date"] = calc_date
        # 如果传 org_code，就只查某个机构。
        if org_code:
            where_parts.append("toString(`org_code`) = {org_code:String}")
            params["org_code"] = org_code
        # 如果传 product_code，就只查某个商品。
        if product_code:
            where_parts.append("toString(`product_code`) = {product_code:String}")
            params["product_code"] = product_code

        # 有过滤条件就拼 WHERE，没有则查默认最近结果。
        where_clause = f"WHERE {' AND '.join(where_parts)} " if where_parts else ""
        # 查询字段全部 quote，避免字段名和关键字冲突。
        select_clause = ", ".join(self._quote_identifier(column) for column in columns)
        # 拼结果表查询 SQL。
        query = (
            # SELECT 指定列清单。
            f"SELECT {select_clause} "
            # FROM 指定结果表。
            f"FROM {table_name} "
            # 插入可选 WHERE。
            f"{where_clause}"
            # 默认先看最新计算日、最新写入时间、最新 run_id。
            "ORDER BY calc_date DESC, created_at DESC, run_id DESC, org_code, product_code "
            # limit 使用参数绑定。
            "LIMIT {limit:UInt64}"
        )
        # 执行查询并返回字典列表。
        return self._query_dicts(query, params)

    def _query_dicts(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """执行查询并返回字典行。"""
        # client.query 返回结果对象，包含 column_names 和 result_rows。
        result = self.client.query(query, parameters=params)
        # 把每一行 tuple 和列名 zip 成 dict，方便 service/core 使用。
        return [
            # strict=False 表示列名和行值长度不一致时不抛异常；这里主要是兼容旧 Python 语义。
            dict(zip(result.column_names, row, strict=False))
            # 遍历 ClickHouse 返回的全部数据行。
            for row in result.result_rows
        ]

    def _sales_select_clause(self) -> str:
        """生成销售视图 SELECT 字段片段。"""
        # 使用 ViewSalesDailyClean mapper，表别名固定为 v。
        return self._select_clause(ViewSalesDailyClean, alias="v")

    def _product_select_clause(self) -> str:
        """生成商品档案表 SELECT 字段片段。"""
        # 使用 DimProduct mapper，表别名固定为 p。
        return self._select_clause(DimProduct, alias="p")

    def _stock_select_clause(self) -> str:
        """生成库存表 SELECT 字段片段。"""
        # 使用 DwdProductStock mapper，表别名固定为 s。
        return self._select_clause(DwdProductStock, alias="s")

    def _sales_daily_table(self) -> str:
        """返回已转义的销售视图表名。"""
        # 表名来自配置，可能是 view_sales_daily_clean，也可能带库名。
        return self._quote_table_name(self.settings.clickhouse_sales_daily_table)

    def _dim_product_table(self) -> str:
        """返回已转义的商品档案表名。"""
        # 表名来自配置，默认 dim_product。
        return self._quote_table_name(self.settings.clickhouse_dim_product_table)

    def _product_stock_table(self) -> str:
        """返回已转义的库存表名。"""
        # 表名来自配置，默认 dwd_product_stock。
        return self._quote_table_name(self.settings.clickhouse_product_stock_table)

    def _alert_result_table(self) -> str:
        """返回已转义的预警结果表名。"""
        # 表名来自配置，默认 ads_inventory_alert_result。
        return self._quote_table_name(self.settings.clickhouse_alert_result_table)

    def _forecast_result_table(self) -> str:
        """返回已转义的补货结果表名。"""
        # 表名来自配置，默认 ads_replenishment_forecast_result。
        return self._quote_table_name(self.settings.clickhouse_forecast_result_table)

    def _sales_expr(self, field_name: str) -> str:
        """返回销售视图某个代码字段对应的 SQL 表达式。"""
        # 例如 field_name='sku'，可能返回 v.`sku_id`。
        return self._mapper_expr(
            mapper=ViewSalesDailyClean,
            alias="v",
            field_name=field_name,
            table_label="view_sales_daily_clean",
        )

    def _product_expr(self, field_name: str) -> str:
        """返回商品档案表某个代码字段对应的 SQL 表达式。"""
        # 例如 field_name='product_code'，真实库中返回 p.`sku_id`。
        return self._mapper_expr(
            mapper=DimProduct,
            alias="p",
            field_name=field_name,
            table_label="dim_product",
        )

    def _stock_expr(self, field_name: str) -> str:
        """返回库存表某个代码字段对应的 SQL 表达式。"""
        # 例如 field_name='org_code'，返回 s.`org_code`。
        return self._mapper_expr(
            mapper=DwdProductStock,
            alias="s",
            field_name=field_name,
            table_label="dwd_product_stock",
        )

    def _select_clause(self, mapper: type, alias: str) -> str:
        """根据 mapper 自动生成 SELECT 子句。

        mapper.columns 的 key 是代码里统一使用的字段名；
        value 是 ClickHouse 真实物理列名。
        """
        # 把每个字段拼成：alias.`物理列名` AS `代码字段名`。
        return ", ".join(
            (
                f"{self._mapper_expr(mapper, alias, field_name)} "
                f"AS {self._quote_identifier(field_name)}"
            )
            # 按 mapper 中字段定义顺序遍历。
            for field_name in mapper.columns
        )

    def _mapper_expr(
        self,
        mapper: type,
        alias: str,
        field_name: str,
        table_label: str | None = None,
    ) -> str:
        """把代码字段名转换成 SQL 字段表达式。

        例如：
            mapper=DimProduct, alias='p', field_name='product_code'
        可能返回：
            p.`sku_id`
        """
        try:
            # 从 mapper 中找到代码字段对应的真实 ClickHouse 物理列名。
            column_name = mapper.columns[field_name]
        except KeyError as exc:
            # 如果 mapper 里没有这个字段，说明代码和字段映射不一致。
            source_name = table_label or getattr(mapper, "__tablename__", mapper.__name__)
            # 抛出清晰错误，提示哪个源对象缺少哪个字段映射。
            raise ClickHouseSchemaError(
                f"没有为字段 {field_name} 配置 {source_name} 列名"
            ) from exc
        # 返回带表别名、且字段名已反引号转义的 SQL 表达式。
        return f"{alias}.{self._quote_identifier(column_name)}"

    def _quote_table_name(self, table_name: str) -> str:
        """安全转义表名。

        支持两种写法：
        - table
        - database.table

        会分别对每一段加反引号。
        """
        # 按点号拆分表名，支持 db.table。
        return ".".join(
            # 对每一段调用 _quote_identifier。
            self._quote_identifier(part)
            # 跳过空字符串，避免多余点号导致 SQL 错误。
            for part in table_name.split(".")
            if part
        )

    def _quote_identifier(self, identifier: str) -> str:
        """安全转义 ClickHouse 标识符。"""
        # ClickHouse 标识符用反引号包裹；内部反引号需要变成两个反引号。
        return f"`{identifier.replace('`', '``')}`"
