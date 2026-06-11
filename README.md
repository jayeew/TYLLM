# Inventory Forecast Demo

基于 FastAPI + ClickHouse 的库存预警与补货预测项目。

当前阶段只使用 `view_sales_daily_clean`、`dim_product` 和 `dwd_product_stock` 三张表/视图计算初版库存预警与补货预测，并把结果追加写入 ClickHouse 快照表。

## 功能范围

- 手动触发库存预警计算并写入 `ads_inventory_alert_result`
- 手动触发补货预测计算并写入 `ads_replenishment_forecast_result`
- 从 ClickHouse 读取 `view_sales_daily_clean`
- 从 ClickHouse 读取 `dim_product` 商品档案
- 从 ClickHouse 读取 `dwd_product_stock` 商品库存
- 通过 API 查询预警/预测结果快照

## 项目结构

```text
inventory_forecast_demo/
├── app/
│   ├── api/
│   ├── config/
│   ├── core/
│   ├── mappers/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   ├── tasks/
│   └── main.py
├── requirements.txt
├── .env
└── README.md
```

## 环境准备

建议使用 Python 3.11+，并确保应用服务器可以访问 ClickHouse。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## ClickHouse 配置

项目固定使用 ClickHouse，不提供其他数据库连接选项。运行配置、业务变量和规则因子都放在 `.env` 中。

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

ALERT_LEVEL1_COVERAGE_DAYS=14
ALERT_LEVEL2_COVERAGE_DAYS=7
ALERT_LEVEL3_COVERAGE_DAYS=3
ALERT_DEFAULT_SAFETY_STOCK_QTY=0
ALERT_EXPIRING_STOCK_RATIO_LIMIT=0.5

REPLENISH_DEFAULT_PURCHASE_CYCLE_DAYS=3
REPLENISH_SAFETY_BUFFER_DAYS=2
REPLENISH_DEFAULT_MIN_ORDER_QTY=1
REPLENISH_DEFAULT_PACK_QTY=1
```

结果表建表语句位于 `sql/预警补货结果表.sql`。服务触发计算时也会自动执行 `CREATE TABLE IF NOT EXISTS`。

初版能计算近 7/15/30 天日均销量、库存覆盖天数、修正后日需求、安全库存缺口、补货缺口和建议补货数量。批次效期、破损、预订、采购流水和真实客流字段当前缺失，相关逻辑在核心代码中保留 TODO，并写入结果表的 `missing_fields`。

## 启动服务

```bash
uvicorn app.main:app --reload --port 8000
```

## 本地脚本触发

不启动 FastAPI 服务时，也可以直接通过本地脚本触发计算流程：

```bash
./run_local.sh --mode all
./run_local.sh --mode alerts --org-code 10001 --sku 0120005
./run_local.sh --mode forecasts --org-code 10001 --calc-date 2026-06-11 --limit 10
```

`--mode` 支持 `all`、`alerts`、`forecasts`，不传时默认执行 `all`。

## API 测试

健康检查：

```bash
curl http://localhost:8000/api/v1/health
```

触发库存预警计算：

```bash
curl -X POST http://localhost:8000/api/v1/alerts/scan \
  -H "Content-Type: application/json" \
  -d '{"calc_date":"2026-06-11","limit":10}'
```

查询库存预警结果：

```bash
curl "http://localhost:8000/api/v1/alerts?calc_date=2026-06-11&limit=10"
```

触发补货预测计算：

```bash
curl -X POST http://localhost:8000/api/v1/forecasts/calculate \
  -H "Content-Type: application/json" \
  -d '{"calc_date":"2026-06-11","limit":10}'
```

查询补货预测结果：

```bash
curl "http://localhost:8000/api/v1/forecasts?calc_date=2026-06-11&limit=10"
```

查询商品档案源表记录：

```bash
curl "http://localhost:8000/api/v1/products/dim-product?product_code=0120005&limit=10"
```

查询商品库存源表记录：

```bash
curl "http://localhost:8000/api/v1/products/stock?org_code=10001&product_code=0120005&limit=10"
```

## 接口列表

- `GET /api/v1/health`
- `POST /api/v1/alerts/scan`
- `GET /api/v1/alerts`
- `POST /api/v1/forecasts/calculate`
- `GET /api/v1/forecasts`
- `GET /api/v1/products/dim-product`
- `GET /api/v1/products/stock`

## 说明

- 结果采用追加快照，不覆盖历史批次。
- 初版以 `dwd_product_stock` 的门店商品库存行为主驱动。
- 缺少的批次效期、采购流水、真实客流等字段不会阻塞计算，但会记录在 `missing_fields`。
