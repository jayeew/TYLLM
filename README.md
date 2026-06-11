# Inventory Forecast Demo

基于 FastAPI + ClickHouse 的库存预警与补货预测占位项目。

当前阶段只保留对 `view_sales_daily_clean` 的读取处理；所有预警、补货预测和指标计算规则均留空，用注释占位，不写入结果表。

## 功能范围

- 手动触发库存预警占位流程
- 手动触发补货预测占位流程
- 从 ClickHouse 读取 `view_sales_daily_clean`
- 通过 API 查询空的预警/预测占位结果

## 项目结构

```text
inventory_forecast_demo/
├── app/
│   ├── api/
│   ├── config/
│   ├── core/
│   ├── mappers/
│   ├── schemas/
│   ├── services/
│   ├── sources/
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
```

`view_sales_daily_clean` 当前字段映射位于 `app/mappers/view_sales_daily_clean.py`。代码只读取该视图中的原始日销售记录，不计算近 7 天销量、日均销量、库存、在途、安全库存、补货数量或预警等级。

## 启动服务

```bash
uvicorn app.main:app --reload --port 8000
```

## 本地脚本触发

不启动 FastAPI 服务时，也可以直接通过本地脚本触发占位流程：

```bash
./run_local.sh --mode all
./run_local.sh --mode alerts --org-code 10001 --sku 0120005
./run_local.sh --mode forecasts --org-code 10001
```

`--mode` 支持 `all`、`alerts`、`forecasts`，不传时默认执行 `all`。

## API 测试

健康检查：

```bash
curl http://localhost:8000/api/v1/health
```

触发库存预警占位流程：

```bash
curl -X POST http://localhost:8000/api/v1/alerts/scan \
  -H "Content-Type: application/json" \
  -d '{}'
```

查询库存预警占位结果：

```bash
curl http://localhost:8000/api/v1/alerts
```

触发补货预测占位流程：

```bash
curl -X POST http://localhost:8000/api/v1/forecasts/calculate \
  -H "Content-Type: application/json" \
  -d '{}'
```

查询补货预测占位结果：

```bash
curl http://localhost:8000/api/v1/forecasts
```

## 接口列表

- `GET /api/v1/health`
- `POST /api/v1/alerts/scan`
- `GET /api/v1/alerts`
- `POST /api/v1/forecasts/calculate`
- `GET /api/v1/forecasts`

## 说明

- 预警、补货预测、指标计算和结果查询均为占位实现。
- 后续只有在业务规则、字段口径和可用数据对象被重新确认后，才新增计算或落库逻辑。
- 不要在代码中猜测规则、字段含义或替代数据来源。
