# TYLLM Project Guide

当前项目是一个 `FastAPI + ClickHouse` 的占位服务。现阶段只保留对
`view_sales_daily_clean` 的读取处理；库存预警、补货预测、指标计算和结果落库均未实现，只保留明确的 TODO 占位。

## 当前边界

- 唯一读取的数据对象：`view_sales_daily_clean`。
- 唯一有效输入字段映射：`app/mappers/view_sales_daily_clean.py`。
- 不读取库存表、商品档案表、交易明细表或任何结果表。
- 不写入预警结果表或预测结果表。
- 不计算日均销量、修正因子、安全库存、有效库存、在途数量、预警等级、补货数量或到货时间。
- 所有业务变量、规则因子和连接配置都从 `.env` 读取；当前规则因子只作为占位配置保留。

## 目录结构

```text
app/
├── api/                 FastAPI 路由层
│   └── v1/
│       ├── alert_api.py
│       ├── forecast_api.py
│       ├── health_api.py
│       └── router.py
├── config/              配置和 ClickHouse client
│   ├── config.py
│   └── database.py
├── core/                业务规则占位
│   ├── alert_rule.py
│   ├── forecast_rule.py
│   └── indicator_calculator.py
├── mappers/             ClickHouse 视图字段映射
│   └── view_sales_daily_clean.py
├── repositories/        当前无活动仓储，仅保留包目录
├── schemas/             API 请求/响应模型
├── services/            应用服务层
├── sources/             ClickHouse 源数据读取
├── tasks/               本地脚本入口
└── main.py              FastAPI app 入口
```

## 模块职责

### `app/main.py`

创建 FastAPI app，并按 `.env` 中的 `API_PREFIX` 挂载 v1 路由。

### `app/api/`

API 层只负责请求接入、依赖注入和响应模型包装，不写业务规则。

- `api/deps.py`：预留请求校验入口，当前 `verify_request()` 直接返回 `True`。
- `api/v1/router.py`：聚合 health、alerts、forecasts 三组路由。
- `api/v1/health_api.py`：健康检查。
- `api/v1/alert_api.py`：触发库存预警占位流程，查询空的预警占位结果。
- `api/v1/forecast_api.py`：触发补货预测占位流程，查询空的预测占位结果。

### `app/config/`

配置层集中读取 `.env`，并创建 ClickHouse client。

- `config.py`：定义 `Settings`。所有字段必须来自 `.env`，代码里不设置业务默认值。
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
```

`.env` 中的预警/补货因子目前只是占位变量，不参与任何计算。

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

新增字段时，先在这里显式增加映射，再决定是否让 source 层查询该字段。

### `app/sources/`

源数据层负责从 ClickHouse 读取 `view_sales_daily_clean` 原始记录。

`sources/clickhouse.py` 当前只做这些事：

- 按 `.env` 创建或复用 ClickHouse 连接。
- 从 `ViewSalesDailyClean.columns` 生成 SELECT 列。
- 支持按 `org_code` 和 `sku` 过滤。
- 使用 ClickHouse query parameters 绑定过滤值。
- quote 表名和字段名。
- 返回 `list[dict]` 原始查询结果。

这里不做类型转换、不做字段语义推断、不做计算。

### `app/core/`

核心规则层当前全是空实现。

- `alert_rule.py`：`judge_alerts()` 固定返回空列表。
- `forecast_rule.py`：`calculate_forecast()` 固定返回 `None`。
- `indicator_calculator.py`：`build_sales_indicators()` 固定返回空 dict。

这些文件只保留 TODO 注释。后续规则、公式、字段口径被确认前，不要在这里添加推测逻辑。

### `app/services/`

服务层串联 API、source 和 core。

- `alert_service.py`：读取 `view_sales_daily_clean`，调用空的 `judge_alerts()`，返回扫描数量和未生成结果的提示。
- `forecast_service.py`：读取 `view_sales_daily_clean`，调用空的 `calculate_forecast()`，返回计算数量和未生成结果的提示。
- `query_service.py`：结果查询占位，`list_alerts()` 和 `list_forecasts()` 都返回空列表。

服务层当前不会清理、创建、写入或查询结果表。

### `app/schemas/`

API 请求/响应模型。

- `common.py`：统一 Pydantic 基类和健康检查响应。
- `alert_schema.py`：预警扫描请求、预警扫描响应、预警列表响应。
- `forecast_schema.py`：补货预测请求、补货预测响应、预测列表响应。

列表响应当前是 `items: list[dict]`，因为结果明细口径尚未确认。

### `app/tasks/`

本地命令行触发入口。

- `local_runner.py`：解析 `--mode`、`--org-code`、`--sku`，调用对应服务。
- `demo_runner.py`：顺序执行预警占位流程和补货预测占位流程。

脚本入口：

```bash
./run_local.sh --mode all
./run_local.sh --mode alerts --org-code 10001 --sku 0120005
./run_local.sh --mode forecasts --org-code 10001
```

## 请求流程

### 预警占位流程

```text
POST /api/v1/alerts/scan
  -> alert_api.scan_alerts()
  -> AlertService.scan_alerts()
  -> ClickHouseSourceRepo.list_sales_daily_records()
  -> core.judge_alerts()
  -> 返回 scanned_count 和 generated_count=0
```

### 补货预测占位流程

```text
POST /api/v1/forecasts/calculate
  -> forecast_api.calculate_forecasts()
  -> ForecastService.calculate_forecasts()
  -> ClickHouseSourceRepo.list_sales_daily_records()
  -> core.calculate_forecast()
  -> 返回 calculated_count 和 generated_count=0
```

### 查询占位流程

```text
GET /api/v1/alerts
  -> QueryService.list_alerts()
  -> 返回 []

GET /api/v1/forecasts
  -> QueryService.list_forecasts()
  -> 返回 []
```

## API 列表

- `GET /api/v1/health`
- `POST /api/v1/alerts/scan`
- `GET /api/v1/alerts`
- `POST /api/v1/forecasts/calculate`
- `GET /api/v1/forecasts`

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

确认前不要新增推测计算，不要从 `view_sales_daily_clean` 推导库存含义，也不要重新接入旧表或结果表。

如果未来确认要新增数据源，建议按这个顺序改：

1. 在 `app/mappers/` 增加显式字段映射。
2. 在 `app/sources/` 增加只读方法。
3. 在 `app/core/` 添加已确认的纯规则函数。
4. 在 `app/services/` 串联流程。
5. 最后再决定是否新增 repository 和结果表写入。

编码字段如 `sku`、`org_code`、条码和品类编码都按字符串处理，避免丢失前导零。
