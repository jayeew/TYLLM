# Inventory Forecast Demo

基于 FastAPI + PostgreSQL 的库存预警与补货预测初版 Demo。

## 功能范围

- 导入基础数据、收银数据、库存快照数据
- 手动触发库存预警扫描
- 手动触发补货需求预测
- 结果写入 PostgreSQL
- 通过 API 查询预警结果和预测结果

## 项目结构

```text
inventory_forecast_demo/
├── app/
│   ├── api/
│   ├── calculations/
│   ├── core/
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   ├── tasks/
│   └── main.py
├── sql/
│   ├── 01_schema.sql
│   └── 02_seed_demo_data.sql
├── requirements.txt
├── .env.example
└── README.md
```

## 环境准备

建议使用 Python 3.11+ 和 PostgreSQL 14+。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 创建数据库

```bash
createdb inventory_forecast_demo
```

如果你已经有 PostgreSQL 数据库，也可以直接修改 `.env` 中的连接配置：

```env
POSTGRES_RECORDMANAGER_HOST=127.0.0.1
POSTGRES_RECORDMANAGER_PORT=5432
POSTGRES_RECORDMANAGER_DATABASE=inventory_forecast_demo
POSTGRES_RECORDMANAGER_USER=postgres
POSTGRES_RECORDMANAGER_PASSWORD=postgres
```

如果配置了完整的 `DATABASE_URL`，系统会优先使用 `DATABASE_URL`。

## 初始化表结构和演示数据

```bash
psql -d inventory_forecast_demo -f sql/01_schema.sql
psql -d inventory_forecast_demo -f sql/02_seed_demo_data.sql
```

## 启动服务

```bash
uvicorn app.main:app --reload --port 8000
```

## API 测试

健康检查：

```bash
curl http://localhost:8000/api/v1/health
```

触发库存预警扫描：

```bash
curl -X POST http://localhost:8000/api/v1/alerts/scan \
  -H "Content-Type: application/json" \
  -d '{}'
```

查询库存预警结果：

```bash
curl http://localhost:8000/api/v1/alerts
```

触发补货需求预测：

```bash
curl -X POST http://localhost:8000/api/v1/forecasts/calculate \
  -H "Content-Type: application/json" \
  -d '{}'
```

查询补货预测结果：

```bash
curl http://localhost:8000/api/v1/forecasts
```

按门店和 SKU 触发预警扫描：

```bash
curl -X POST http://localhost:8000/api/v1/alerts/scan \
  -H "Content-Type: application/json" \
  -d '{"store_code":"STORE001","sku":1001001}'
```

按门店和 SKU 查询预警：

```bash
curl "http://localhost:8000/api/v1/alerts?store_code=STORE001&sku=1001001"
```

## 接口列表

- `GET /api/v1/health`
- `POST /api/v1/alerts/scan`
- `GET /api/v1/alerts`
- `POST /api/v1/forecasts/calculate`
- `GET /api/v1/forecasts`

## 说明

- 数据库字段名保留中文，ORM 使用英文属性映射。
- Demo 运行时会在指定过滤条件下清空旧的预警/预测结果，便于重复测试。
- `app/tasks/demo_runner.py` 提供了同时执行扫描和预测的简单入口，适合后续接定时任务。
