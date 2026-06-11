# TYLLM Project Guide

当前项目是一个 `FastAPI + ClickHouse` 的库存预警与补货预测服务。现阶段只使用
`view_sales_daily_clean`、`dim_product` 和 `dwd_product_stock` 三张表/视图计算初版结果，并追加写入预警和补货结果快照表。

## 当前边界

- 当前读取的数据对象：`view_sales_daily_clean`、`dim_product`、`dwd_product_stock`。
- 当前有效输入字段映射：`app/mappers/view_sales_daily_clean.py`、`app/mappers/dim_product.py`、`app/mappers/dwd_product_stock.py`。
- 当前写入结果对象：`ads_inventory_alert_result`、`ads_replenishment_forecast_result`。
- 不读取交易明细表、采购流水表、批次效期表或真实客流表。
- 能计算日均销量、修正因子、库存覆盖、安全库存缺口、预警等级、在途数量、补货数量和建议日期。
- 缺失的批次效期、破损、预订、采购流水、真实客流等字段在核心代码保留 TODO，并写入 `missing_fields`。

## 目录结构

```text
app/
├── api/                 FastAPI 路由层
│   └── v1/
│       ├── alert_api.py
│       ├── forecast_api.py
│       ├── health_api.py
│       ├── product_api.py
│       └── router.py
├── config/              配置和 ClickHouse client
│   ├── config.py
│   └── database.py
├── core/                业务规则占位
│   ├── alert_rule.py
│   ├── forecast_rule.py
│   └── indicator_calculator.py
├── mappers/             ClickHouse 视图和源表字段映射
│   ├── dim_product.py
│   ├── dwd_product_stock.py
│   └── view_sales_daily_clean.py
├── repositories/        ClickHouse 源表、计算输入和结果表仓储
├── schemas/             API 请求/响应模型
├── services/            应用服务层
├── tasks/               本地脚本入口
└── main.py              FastAPI app 入口
```

## 模块职责

### `app/main.py`

创建 FastAPI app，并按 `.env` 中的 `API_PREFIX` 挂载 v1 路由。

### `app/api/`

API 层只负责请求接入、依赖注入和响应模型包装，不写业务规则。

- `api/deps.py`：预留请求校验入口，当前 `verify_request()` 直接返回 `True`。
- `api/v1/router.py`：聚合 health、alerts、forecasts、products 四组路由。
- `api/v1/health_api.py`：健康检查。
- `api/v1/alert_api.py`：触发库存预警计算，查询预警结果快照。
- `api/v1/forecast_api.py`：触发补货预测计算，查询补货结果快照。
- `api/v1/product_api.py`：查询 `dim_product` 和 `dwd_product_stock` 原始记录。

### `app/config/`

配置层集中读取 `.env`，并创建 ClickHouse client。

- `config.py`：定义 `Settings`。连接配置和业务因子来自 `.env`，源表表名和查询上限可通过 `.env` 覆盖。
- `database.py`：创建并复用 ClickHouse client，同时把 ClickHouse 内网地址加入 `NO_PROXY`。

当前关键配置：

```env
APP_NAME=inventory-forecast-demo
API_PREFIX=/api/v1
CLICKHOUSE_HOST=172.33.22.160
CLICKHOUSE_PORT=8123
CLICKHOUSE_DATABASE=sales_db
CLICKHOUSE_USER=tjsk
CLICKHOUSE_PASSWORD=123456
CLICKHOUSE_SECURE=False
CLICKHOUSE_CONNECT_TIMEOUT=10
CLICKHOUSE_SEND_RECEIVE_TIMEOUT=60
CLICKHOUSE_SALES_DAILY_TABLE=view_sales_daily_clean
CLICKHOUSE_SALES_DAILY_QUERY_LIMIT=1000
CLICKHOUSE_DIM_PRODUCT_TABLE=dim_product
CLICKHOUSE_DIM_PRODUCT_QUERY_LIMIT=1000
CLICKHOUSE_PRODUCT_STOCK_TABLE=dwd_product_stock
CLICKHOUSE_PRODUCT_STOCK_QUERY_LIMIT=1000
CLICKHOUSE_ALERT_RESULT_TABLE=ads_inventory_alert_result
CLICKHOUSE_FORECAST_RESULT_TABLE=ads_replenishment_forecast_result
CLICKHOUSE_RESULT_QUERY_LIMIT=1000
```

`.env` 中同时维护预警阈值、补货默认进货周期、安全缓冲天数、最小订货量和默认箱规。

### `app/mappers/`

映射层只维护 ClickHouse 物理列名和代码内部字段名的对应关系。当前不再使用 SQLAlchemy mapper。

`view_sales_daily_clean.py` 中的字段映射：

- `sale_date` -> `date`
- `sku` -> `sku_id`
- `product_name` -> `sku_name`
- `org_code` -> `store_id`
- `store_name` -> `store_name`
- `unit` -> `unit`
- `sales_qty` -> `sales`
- `avg_price` -> `avg_price`
- `sales_amount` -> `sales_amount`
- `trans_cnt` -> `trans_cnt`
- `cashier_cnt` -> `cashier_cnt`

`dim_product.py` 和 `dwd_product_stock.py` 按建表 SQL 中的列名一一显式映射。新增字段时，先在这里显式增加映射，再决定是否让 repository 层查询该字段。

### `app/repositories/`

仓储层负责所有直接对接 ClickHouse 的操作。Service 层不直接拼 SQL、不直接调用 `client.query()` 或 `client.insert()`。

当前主要仓储如下：

- `sales_daily_repo.py`：读取 `view_sales_daily_clean`。
- `dim_product_repo.py`：读取 `dim_product`。
- `product_stock_repo.py`：读取 `dwd_product_stock`。
- `inventory_calculation_repo.py`：以库存表为主驱动，左关联商品档案，并聚合销售视图最近 7/15/30 天销量。
- `inventory_alert_result_repo.py`：创建、写入、查询预警结果表。
- `replenishment_forecast_result_repo.py`：创建、写入、查询补货预测结果表。
- `clickhouse_base.py`：封装通用 `query -> list[dict]` 和批量 insert。

这里不做业务计算；公式和缺字段口径集中在 `app/core/`。

### `app/core/`

核心规则层实现初版公式。

- `indicator_calculator.py`：计算 7/15/30 天销量回退、修正因子、日需求、覆盖天数、预计销售天数。
- `alert_rule.py`：根据覆盖天数和安全库存缺口生成一级/二级/三级预警或库存充足状态。
- `forecast_rule.py`：计算补货周期需求、安全库存、在途、缺口、MOQ/箱规取整和建议日期。

批次效期、破损、预订、采购流水、客流趋势等当前缺字段逻辑只保留 TODO，不做隐式推断。

### `app/services/`

服务层串联 API、source 和 core。

- `alert_service.py`：读取库存驱动计算输入，调用 `judge_alerts()`，写入预警结果表。
- `forecast_service.py`：读取库存驱动计算输入，调用 `calculate_forecasts()`，写入补货结果表。
- `product_service.py`：读取 `dim_product` 和 `dwd_product_stock` 原始记录。
- `query_service.py`：查询预警和补货结果表，支持 `run_id`、`calc_date`、`org_code`、`sku`、`limit`。

服务层会自动创建结果表，但不会清理或覆盖历史结果。

### `app/schemas/`

API 请求/响应模型。

- `common.py`：统一 Pydantic 基类和健康检查响应。
- `alert_schema.py`：预警扫描请求、预警扫描响应、预警列表响应。
- `forecast_schema.py`：补货预测请求、补货预测响应、预测列表响应。
- `product_schema.py`：商品档案列表响应、商品库存列表响应。

列表响应当前是 `items: list[dict]`，直接返回 ClickHouse 结果快照行。

### `app/tasks/`

本地命令行触发入口。

- `local_runner.py`：解析 `--mode`、`--org-code`、`--sku`、`--calc-date`、`--limit`，调用对应服务。
- `demo_runner.py`：顺序执行预警流程和补货预测流程。

脚本入口：

```bash
./run_local.sh --mode all
./run_local.sh --mode alerts --org-code 10001 --sku 0120005
./run_local.sh --mode forecasts --org-code 10001 --calc-date 2026-06-11 --limit 10
```

## 请求流程

### 预警流程

```text
POST /api/v1/alerts/scan
  -> alert_api.scan_alerts()
  -> AlertService.scan_alerts()
  -> InventoryCalculationRepo.list_inputs()
  -> core.judge_alerts()
  -> InventoryAlertResultRepo.insert_many()
  -> 返回 run_id、scanned_count、generated_count、written_count
```

### 补货预测流程

```text
POST /api/v1/forecasts/calculate
  -> forecast_api.calculate_forecasts()
  -> ForecastService.calculate_forecasts()
  -> InventoryCalculationRepo.list_inputs()
  -> core.calculate_forecasts()
  -> ReplenishmentForecastResultRepo.insert_many()
  -> 返回 run_id、calculated_count、generated_count、written_count
```

### 查询流程

```text
GET /api/v1/alerts
  -> QueryService.list_alerts()
  -> InventoryAlertResultRepo.list_records()
  -> 返回 ads_inventory_alert_result 快照

GET /api/v1/forecasts
  -> QueryService.list_forecasts()
  -> ReplenishmentForecastResultRepo.list_records()
  -> 返回 ads_replenishment_forecast_result 快照

GET /api/v1/products/dim-product
  -> ProductService.list_dim_products()
  -> DimProductRepo.list_records()
  -> 返回 dim_product 原始记录

GET /api/v1/products/stock
  -> ProductService.list_product_stocks()
  -> ProductStockRepo.list_records()
  -> 返回 dwd_product_stock 原始记录
```

## API 列表

- `GET /api/v1/health`
- `POST /api/v1/alerts/scan`
- `GET /api/v1/alerts`
- `POST /api/v1/forecasts/calculate`
- `GET /api/v1/forecasts`
- `GET /api/v1/products/dim-product`
- `GET /api/v1/products/stock`

## 依赖说明

当前 `requirements.txt` 保留：

- `fastapi`
- `uvicorn[standard]`
- `clickhouse-connect`
- `pydantic`
- `pydantic-settings`
- `python-dotenv`

项目当前不需要 SQLAlchemy，也不需要 Postgres 相关依赖。

## 扩展原则

后续扩展必须先确认三件事：

1. 可用数据对象是否真实可靠。
2. 字段口径是否明确。
3. 业务规则和计算公式是否明确。

确认前不要从 `view_sales_daily_clean`、`dim_product` 或 `dwd_product_stock` 之外的数据对象推导尚未确认的业务含义。

如果未来确认要新增数据源，建议按这个顺序改：

1. 在 `app/mappers/` 增加显式字段映射。
2. 在 `app/repositories/` 增加只读仓储方法。
3. 在 `app/core/` 添加已确认的纯规则函数。
4. 在 `app/services/` 串联流程。
5. 最后再决定是否新增结果表写入。

编码字段如 `sku`、`org_code`、条码和品类编码都按字符串处理，避免丢失前导零。
