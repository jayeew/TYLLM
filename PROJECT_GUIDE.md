# 库存预警与补货预测 Demo 项目详解

这份文档是给 Web 开发初学者看的项目导览。它会从 `app/main.py` 开始，顺着一次真实接口请求的运行路径，讲清楚每一层代码在做什么、数据是怎么一层一层传递的，以及最后结果是怎么写入数据库并返回给前端或调用方的。

读完以后，你应该能回答这几个问题：

- 项目启动时先运行哪个文件？
- 请求是怎么从 URL 找到具体 Python 函数的？
- API 层、Service 层、Repository 层、Calculation 层分别负责什么？
- 数据库连接是怎么创建、传递和关闭的？
- 请求体、数据库对象、响应 JSON 之间是怎么转换的？
- 库存预警和补货预测的核心业务流程是什么？

## 1. 项目整体在做什么

这个项目是一个基于 `FastAPI + PostgreSQL + SQLAlchemy` 的后端 Demo，用来验证库存业务闭环。

业务闭环可以理解成下面这条线：

```text
基础数据、收银数据、库存数据入库
        ↓
手动调用接口触发库存预警扫描
        ↓
系统计算近 7 天销量、库存覆盖天数、效期风险
        ↓
生成库存预警结果并写入数据库
        ↓
手动调用接口触发补货预测
        ↓
系统计算建议补货数量和预计到货时间
        ↓
生成补货预测结果并写入数据库
        ↓
通过 API 查询预警结果和预测结果
```

当前项目只做后端，不包含前端页面、小程序、登录鉴权、大模型问答、Redis 缓存等复杂能力。它的重点是先证明核心业务逻辑可以跑通。

## 2. 项目目录怎么理解

项目主要目录如下：

```text
app/
├── main.py                  # FastAPI 应用入口
├── config/                  # 配置和数据库连接
├── api/                     # 接口层，负责接收 HTTP 请求
├── schemas/                 # Pydantic 数据模型，负责请求和响应结构
├── services/                # 业务服务层，负责组织完整业务流程
├── repositories/            # 数据访问层，负责查询和写入数据库
├── core/                    # 计算规则层，负责纯业务公式和规则判断
├── mappers/                 # SQLAlchemy ORM 模型，负责映射数据库表
└── tasks/                   # 任务入口，预留给定时任务或批处理

sql/
├── 01_schema.sql            # 建表脚本
└── 02_seed_demo_data.sql    # 演示数据脚本
```

可以把它想象成一家餐厅：

```text
API 层：前台点单，接收客人请求
Service 层：店长安排流程，决定先做什么再做什么
Repository 层：仓库管理员，只负责取货和入库
Calculation 层：厨师手里的配方，只负责怎么算
Models 层：货架标签，说明数据库里的东西在 Python 里叫什么
Schemas 层：菜单和出餐格式，规定请求和响应长什么样
```

这个比喻只是帮助理解，真正开发时你只要记住一句话：每一层只做自己的事，层和层之间通过清晰的数据传递连接起来。

## 3. 服务从哪里启动

启动命令是：

```bash
uvicorn app.main:app --reload --port 8000
```

这条命令可以拆成几部分看：

```text
uvicorn        启动 ASGI Web 服务
app.main       找到 app/main.py 这个 Python 模块
:app           从 app/main.py 里面找到名为 app 的 FastAPI 对象
--reload       代码变化后自动重启，适合开发环境
--port 8000    监听 8000 端口
```

入口文件是 `app/main.py`：

```python
from fastapi import FastAPI

from app.api.v1.router import api_router
from app.config.config import settings


app = FastAPI(title=settings.app_name)
app.include_router(api_router, prefix=settings.api_prefix)
```

这里发生了两件核心事情：

1. `app = FastAPI(title=settings.app_name)` 创建了一个 FastAPI 应用。
2. `app.include_router(api_router, prefix=settings.api_prefix)` 把所有接口注册进来，并统一加上 `/api/v1` 前缀。

所以访问：

```text
GET /api/v1/health
```

本质上就是访问这个 FastAPI 应用里已经注册好的一个路由函数。

## 4. 配置是怎么加载的

配置文件在 `app/config/config.py`。

它使用 `pydantic-settings` 读取 `.env` 文件：

```python
class Settings(BaseSettings):
    app_name: str = "inventory-forecast-demo"
    api_prefix: str = "/api/v1"

    postgres_recordmanager_host: str = "localhost"
    postgres_recordmanager_port: int = 5432
    postgres_recordmanager_database: str = "inventory_forecast_demo"
    postgres_recordmanager_user: str = "postgres"
    postgres_recordmanager_password: str = "postgres"
```

也就是说你可以在 `.env` 里配置：

```env
APP_NAME=inventory-forecast-demo
API_PREFIX=/api/v1

POSTGRES_RECORDMANAGER_HOST=127.0.0.1
POSTGRES_RECORDMANAGER_PORT=5432
POSTGRES_RECORDMANAGER_DATABASE=inventory_forecast_demo
POSTGRES_RECORDMANAGER_USER=postgres
POSTGRES_RECORDMANAGER_PASSWORD=your_password
```

项目里还有一个 `database_url` 属性：

```python
@property
def database_url(self) -> str:
    ...
```

它会把上面的数据库配置拼成 SQLAlchemy 需要的连接字符串：

```text
postgresql+psycopg://用户名:密码@数据库地址:端口/数据库名
```

如果 `.env` 里配置了完整的 `DATABASE_URL`，项目会优先使用 `DATABASE_URL`。如果没有配置，就使用拆分字段自动拼接。

## 5. 数据库连接是怎么创建和传递的

数据库连接代码在 `app/config/database.py`：

```python
engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)
```

这里可以分三层理解：

```text
settings.database_url
        ↓
create_engine(...)
        ↓
SessionLocal()
        ↓
一次请求里真正使用的 db 会话对象
```

`engine` 是数据库连接引擎，可以理解为“怎么连数据库”的总配置。

`SessionLocal` 是会话工厂，可以理解为“每次需要操作数据库时，用它生产一个数据库会话”。

`get_db()` 是 FastAPI 依赖注入函数：

```python
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

它的作用是：

1. 请求开始时创建一个 `db` 会话。
2. 把这个 `db` 传给接口函数。
3. 请求结束后自动关闭 `db`。

这就是层间数据传递里非常关键的一环：API 函数拿到 `db`，再传给 Service，Service 再传给 Repository，Repository 用它真正查库或写库。

## 6. 路由是怎么注册的

总路由文件是 `app/api/v1/router.py`：

```python
api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(alert_router, prefix="/alerts", tags=["alerts"])
api_router.include_router(forecast_router, prefix="/forecasts", tags=["forecasts"])
```

这里注册了三组接口：

```text
health_router      健康检查
alert_router       库存预警相关接口
forecast_router    补货预测相关接口
```

因为 `app/main.py` 里已经给总路由加了 `/api/v1` 前缀，所以最终接口路径会变成：

```text
/api/v1/health
/api/v1/alerts/scan
/api/v1/alerts
/api/v1/forecasts/calculate
/api/v1/forecasts
```

注意：`/api/v1/alerts/scan` 是 `POST` 接口。如果你在浏览器地址栏直接打开，它会发 `GET` 请求，项目会返回 `405 Method Not Allowed`。这是正常现象，因为这个接口设计成必须用 `POST` 调用。

## 7. 一次库存预警请求是怎么跑完的

我们以这个接口为例：

```bash
curl -X POST http://localhost:8000/api/v1/alerts/scan \
  -H "Content-Type: application/json" \
  -d '{"store_code":"STORE001","sku":1001001}'
```

完整流程如下：

```text
HTTP 请求
  ↓
app/main.py
  ↓
api/v1/router.py
  ↓
api/v1/alert_api.py
  ↓
schemas/alert_schema.py
  ↓
services/alert_service.py
  ↓
repositories/inventory_snapshot_repo.py
  ↓
repositories/pos_transaction_repo.py
  ↓
core/indicator_calculator.py
  ↓
core/alert_rule.py
  ↓
repositories/inventory_alert_repo.py
  ↓
PostgreSQL
  ↓
返回 JSON 响应
```

下面一步一步讲。

### 7.1 请求先进入 API 层

代码在 `app/api/v1/alert_api.py`：

```python
@router.post("/scan", response_model=AlertScanResponse)
def scan_alerts(
    payload: AlertScanRequest,
    db: Session = Depends(get_db),
) -> AlertScanResponse:
    service = AlertService(db)
    result = service.scan_alerts(store_code=payload.store_code, sku=payload.sku)
    return AlertScanResponse(**result)
```

这里有几个关键点：

`@router.post("/scan")` 表示这个函数处理 `POST /alerts/scan`。

因为总前缀是 `/api/v1`，所以完整路径是：

```text
POST /api/v1/alerts/scan
```

`payload: AlertScanRequest` 表示请求体会被 Pydantic 自动解析成 `AlertScanRequest` 对象。

请求 JSON：

```json
{
  "store_code": "STORE001",
  "sku": 1001001
}
```

会变成 Python 对象：

```python
payload.store_code == "STORE001"
payload.sku == Decimal("1001001")
```

`db: Session = Depends(get_db)` 表示 FastAPI 会自动调用 `get_db()`，生成一个数据库会话，并传给这个接口函数。

这一层只做三件事：

1. 接收请求。
2. 创建 `AlertService(db)`。
3. 调用 `service.scan_alerts(...)`。

它不直接写 SQL，也不直接判断业务规则。

### 7.2 请求体 Schema 是什么

代码在 `app/schemas/alert_schema.py`：

```python
class AlertScanRequest(AppBaseModel):
    store_code: str | None = None
    sku: Decimal | None = None
```

这表示请求体里 `store_code` 和 `sku` 都是可选字段。

所以这两种请求都合法：

```json
{}
```

```json
{
  "store_code": "STORE001",
  "sku": 1001001
}
```

如果传空对象 `{}`，系统会扫描全部库存快照。

如果传 `store_code` 和 `sku`，系统只扫描指定门店和指定 SKU。

### 7.3 API 层把数据传给 Service 层

API 层调用：

```python
service = AlertService(db)
result = service.scan_alerts(store_code=payload.store_code, sku=payload.sku)
```

这里发生了两次传递：

```text
db 会话对象
API 层 → AlertService

store_code / sku 参数
请求体 payload → AlertService.scan_alerts()
```

Service 层拿到这些东西后，开始组织完整业务流程。

### 7.4 Service 层负责业务编排

代码在 `app/services/alert_service.py`：

```python
class AlertService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.snapshot_repo = InventorySnapshotRepo(db)
        self.pos_repo = PosTransactionRepo(db)
        self.alert_repo = InventoryAlertRepo(db)
        self.base_info_repo = BaseInfoRepo(db)
```

`AlertService` 初始化时，把同一个 `db` 传给多个 Repository：

```text
AlertService
  ├── InventorySnapshotRepo(db)
  ├── PosTransactionRepo(db)
  ├── InventoryAlertRepo(db)
  └── BaseInfoRepo(db)
```

这样做的好处是：同一次请求里的所有数据库操作都使用同一个数据库会话，最后统一 `commit()` 或 `rollback()`。

核心方法是：

```python
def scan_alerts(self, store_code: str | None = None, sku: Decimal | None = None) -> dict:
```

这个方法的流程是：

```text
1. 获取当前时间戳
2. 查询库存快照
3. 查询门店名称
4. 清空旧的 Demo 预警结果
5. 遍历每一条库存快照
6. 查询该门店 SKU 最近 7 天销量
7. 计算日均销量
8. 计算库存覆盖天数
9. 计算距离到期天数
10. 调用预警规则判断是否预警
11. 如果触发预警，组装预警结果
12. 写入 ads_inventory_alert
13. 提交事务
14. 返回扫描数量和生成数量
```

可以看到，Service 层自己不直接写复杂 SQL，也不把计算公式写死在里面。它主要负责“把流程串起来”。

### 7.5 Repository 层负责查库存快照

库存快照查询在 `app/repositories/inventory_snapshot_repo.py`：

```python
def list_inventory_snapshots(
    self,
    store_code: str | None = None,
    sku: Decimal | None = None,
) -> list[FactInventorySnapshot]:
    stmt = select(FactInventorySnapshot).order_by(
        FactInventorySnapshot.store_code,
        FactInventorySnapshot.sku,
    )

    if store_code:
        stmt = stmt.where(FactInventorySnapshot.store_code == store_code)
    if sku is not None:
        stmt = stmt.where(FactInventorySnapshot.sku == sku)

    return list(self.db.scalars(stmt).all())
```

如果请求传了：

```json
{
  "store_code": "STORE001",
  "sku": 1001001
}
```

这里就会生成类似这样的查询条件：

```sql
WHERE "门店编号" = 'STORE001'
  AND "SKU货号" = 1001001
```

返回结果是 `FactInventorySnapshot` 对象列表。

注意：这里返回的不是字典，而是 ORM 对象。比如可以通过下面方式取字段：

```python
snapshot.store_code
snapshot.sku
snapshot.product_name
snapshot.available_qty
```

这些英文属性会自动对应数据库里的中文字段。

### 7.6 ORM 模型负责中英文映射

代码在 `app/mappers/fact_inventory_snapshot.py`：

```python
class FactInventorySnapshot(Base):
    __tablename__ = "fact_inventory_snapshot"

    store_code = mapped_column("门店编号", String, nullable=False)
    product_category = mapped_column("商品类别", Text, nullable=False)
    product_name = mapped_column("商品名称", Text, nullable=False)
    sku = mapped_column("SKU货号", Numeric(20, 0), nullable=False)
    available_qty = mapped_column("可用库存", Numeric(14, 2), nullable=False)
```

数据库字段是中文：

```text
"门店编号"
"商品类别"
"商品名称"
"SKU货号"
"可用库存"
```

Python 代码使用英文：

```text
store_code
product_category
product_name
sku
available_qty
```

这样代码更容易读，同时又能兼容业务数据库的中文字段名。

### 7.7 Repository 层负责查最近 7 天销量

代码在 `app/repositories/pos_transaction_repo.py`：

```python
def sum_sales_qty_last_7_days(
    self,
    store_code: str,
    sku: Decimal,
    now_ts: int,
) -> Decimal:
    seven_days_ago_ts = now_ts - 7 * 86400
    stmt = select(func.coalesce(func.sum(FactPosTransaction.sales_qty), 0)).where(
        FactPosTransaction.store_code == store_code,
        FactPosTransaction.sku == sku,
        FactPosTransaction.transaction_time >= seven_days_ago_ts,
    )
    result = self.db.execute(stmt).scalar_one()
    return Decimal(str(result))
```

这里的业务意思是：

```text
同一个门店
同一个 SKU
交易时间在最近 7 天内
把销售数量加总
```

如果最近 7 天没有销量，`coalesce(sum(...), 0)` 会返回 `0`，避免后面计算时报空值错误。

### 7.8 Calculation 层负责算指标

代码在 `app/core/indicator_calculator.py`：

```python
def calc_avg_daily_sales_7d(total_sales_qty: Decimal) -> Decimal:
    return total_sales_qty / Decimal("7")
```

近 7 天日均销量公式：

```text
近 7 天日均销量 = 最近 7 天销售数量 / 7
```

库存覆盖天数：

```python
def calc_coverage_days(available_qty: Decimal, avg_daily_sales: Decimal) -> Decimal:
    if avg_daily_sales > 0:
        return available_qty / avg_daily_sales
    if available_qty > 0:
        return Decimal("999")
    return Decimal("0")
```

业务含义是：

```text
如果有销量：
    库存覆盖天数 = 可用库存 / 日均销量

如果没有销量，但还有库存：
    覆盖天数 = 999，表示短期内没有销售压力

如果没有销量，也没有库存：
    覆盖天数 = 0
```

距离到期天数：

```python
def calc_days_to_expiry(batch_expiry_ts: int | None, now_ts: int) -> Decimal | None:
    if batch_expiry_ts is None:
        return None
    return Decimal(batch_expiry_ts - now_ts) / Decimal("86400")
```

业务含义是：

```text
距离到期天数 = (批次效期时间戳 - 当前时间戳) / 86400
```

因为一天有 86400 秒。

### 7.9 Alert Rule 负责判断预警

代码在 `app/core/alert_rule.py`：

```python
def judge_alert(snapshot, avg_daily_sales: Decimal, coverage_days: Decimal, days_to_expiry):
```

这个函数输入四个东西：

```text
snapshot          当前库存快照对象
avg_daily_sales   近 7 天日均销量
coverage_days     库存覆盖天数
days_to_expiry    距离到期天数
```

它会按优先级判断：

```text
1. 已过期：过期预警，三级预警
2. 覆盖天数 <= 1：缺货预警，三级预警
3. 覆盖天数 <= 3：低库存预警，二级预警
4. 覆盖天数 <= 5：库存不足预警，一级预警
5. 接近效期：临期预警，二级预警
6. 可用库存低于安全阈值：安全库存预警，一级预警
7. 其他情况：不生成预警
```

函数返回两种结果：

如果触发预警，返回字典：

```python
{
    "category": "缺货预警",
    "level": "三级预警",
    "reason": "库存覆盖天数低于1天",
}
```

如果不触发预警，返回：

```python
None
```

Service 层会根据这个返回值决定是否写入预警结果表。

### 7.10 预警结果是怎么写入数据库的

Service 层组装预警数据：

```python
self.alert_repo.insert_alert(
    {
        "store_code": snapshot.store_code,
        "sku": snapshot.sku,
        "product_name": snapshot.product_name,
        "warning_category": alert_result["category"],
        "warning_time": now_ts,
        "warning_store": warning_store,
        "warning_product_category": snapshot.product_category,
        "warning_level": alert_result["level"],
        "warning_detail": warning_detail,
        "replenishment_suggestion": "建议触发补货预测",
    }
)
```

写入逻辑在 `app/repositories/inventory_alert_repo.py`：

```python
def insert_alert(self, alert_data: dict) -> AdsInventoryAlert:
    alert = AdsInventoryAlert(**alert_data)
    self.db.add(alert)
    self.db.flush()
    return alert
```

这里的 `alert_data` 是一个普通字典。

`AdsInventoryAlert(**alert_data)` 会把字典变成 ORM 对象。

`self.db.add(alert)` 表示告诉 SQLAlchemy：“这个对象需要写入数据库”。

`self.db.flush()` 表示先把 SQL 发给数据库，但事务还没有最终提交。

最后在 Service 层：

```python
self.db.commit()
```

才是真正提交事务。

如果中间任何一步报错：

```python
except Exception:
    self.db.rollback()
    raise
```

就回滚，避免写入一半的数据。

## 8. 一次查询预警结果请求是怎么跑完的

请求示例：

```bash
curl "http://localhost:8000/api/v1/alerts?store_code=STORE001&sku=1001001"
```

流程是：

```text
GET /api/v1/alerts
  ↓
alert_api.py 的 list_alerts()
  ↓
QueryService.list_alerts()
  ↓
InventoryAlertRepo.list_alerts()
  ↓
数据库查询 ads_inventory_alert
  ↓
返回 ORM 对象列表
  ↓
Pydantic 转成 JSON
```

API 代码：

```python
@router.get("", response_model=AlertListResponse)
def list_alerts(
    store_code: str | None = Query(default=None),
    sku: Decimal | None = Query(default=None),
    warning_level: str | None = Query(default=None),
    warning_category: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> AlertListResponse:
    service = QueryService(db)
    items = service.list_alerts(...)
    return AlertListResponse(items=items)
```

这里的查询参数来自 URL：

```text
?store_code=STORE001&sku=1001001
```

FastAPI 会自动把它们传给函数参数：

```python
store_code == "STORE001"
sku == Decimal("1001001")
```

Repository 查询结果是 ORM 对象列表，最后包装成：

```python
AlertListResponse(items=items)
```

Pydantic 会根据 `AlertItem` 的字段，把 ORM 对象转成 JSON。

## 9. 一次补货预测请求是怎么跑完的

请求示例：

```bash
curl -X POST http://localhost:8000/api/v1/forecasts/calculate \
  -H "Content-Type: application/json" \
  -d '{"store_code":"STORE001","sku":1001001}'
```

完整流程如下：

```text
HTTP 请求
  ↓
forecast_api.py
  ↓
ForecastCalculationRequest
  ↓
ForecastService.calculate_forecasts()
  ↓
InventorySnapshotRepo 查库存快照
  ↓
PosTransactionRepo 查最近 7 天销量
  ↓
indicator_calculator 算日均销量
  ↓
forecast_rule 算补货缺口和建议补货数量
  ↓
InventoryForecastRepo 写入预测结果
  ↓
commit 提交事务
  ↓
返回 JSON 响应
```

API 层代码在 `app/api/v1/forecast_api.py`：

```python
@router.post("/calculate", response_model=ForecastCalculationResponse)
def calculate_forecasts(
    payload: ForecastCalculationRequest,
    db: Session = Depends(get_db),
) -> ForecastCalculationResponse:
    service = ForecastService(db)
    result = service.calculate_forecasts(store_code=payload.store_code, sku=payload.sku)
    return ForecastCalculationResponse(**result)
```

跟预警扫描很像：

```text
请求体 → payload
数据库会话 → db
payload + db → ForecastService
业务结果 → ForecastCalculationResponse
```

## 10. 补货预测公式怎么理解

补货计算代码在 `app/core/forecast_rule.py`：

```python
def calculate_forecast(snapshot, avg_daily_sales: Decimal):
```

它需要两个输入：

```text
snapshot          当前库存快照
avg_daily_sales   近 7 天日均销量
```

第一步：计算总到货周期。

```python
total_lead_days = purchase_cycle + delivery_cycle + delivery_days
```

业务含义：

```text
总到货周期 = 进货周期 + 配送周期 + 送货天数
```

第二步：计算修正因子。

```python
factor = base_factor * correction_factor
```

业务含义：

```text
综合修正因子 = 基础修正因子K0 × 修正因子
```

第三步：计算补货周期需求。

```python
cycle_demand = avg_daily_sales * factor * total_lead_days
```

业务含义：

```text
补货周期需求 = 日均销量 × 综合修正因子 × 总到货周期
```

第四步：计算安全库存需求。

```python
safety_stock_need = max(dynamic_safety_stock, avg_daily_sales * safety_buffer_days)
```

业务含义：

```text
安全库存需求 = max(动态安全库存, 日均销量 × 安全缓冲天数)
```

第五步：计算原始补货缺口。

```python
raw_need = cycle_demand + safety_stock_need - available_qty - in_transit_qty
```

业务含义：

```text
原始补货缺口 = 补货周期需求 + 安全库存需求 - 可用库存 - 在途数量
```

第六步：判断是否需要补货。

```python
if raw_need <= 0:
    return None
```

如果缺口小于等于 0，说明不需要补货。

第七步：按最小订货数量向上取整。

```python
suggested_qty = ceil_to_min_order(raw_need, min_order_qty)
```

举例：

```text
原始缺口 = 34
最小订货数量 = 12
34 / 12 = 2.83
向上取整 = 3
建议补货数量 = 3 × 12 = 36
```

所以最后建议补货 `36`。

## 11. 查询补货预测结果是怎么跑完的

请求示例：

```bash
curl "http://localhost:8000/api/v1/forecasts?store_code=STORE001&sku=1001001"
```

流程：

```text
GET /api/v1/forecasts
  ↓
forecast_api.py 的 list_forecasts()
  ↓
QueryService.list_forecasts()
  ↓
InventoryForecastRepo.list_forecasts()
  ↓
查询 ads_inventory_forecast
  ↓
返回 ForecastListResponse
```

可以按这些字段过滤：

```text
store_code         门店编号
sku                SKU 货号
product_category   商品类别
warehouse          仓库
```

## 12. 层间数据传递机制总结

这一节很重要。你可以把一次请求的数据传递分成 5 种对象。

### 12.1 HTTP JSON → Pydantic Request

客户端传入：

```json
{
  "store_code": "STORE001",
  "sku": 1001001
}
```

FastAPI 自动转换成：

```python
AlertScanRequest(store_code="STORE001", sku=Decimal("1001001"))
```

这一步发生在 API 层。

### 12.2 FastAPI Depends → 数据库 Session

接口函数里写：

```python
db: Session = Depends(get_db)
```

FastAPI 会自动执行：

```python
db = SessionLocal()
```

然后把 `db` 传给接口函数。

这一步解决了“每个接口怎么拿数据库连接”的问题。

### 12.3 API 层 → Service 层

API 层调用：

```python
service = AlertService(db)
result = service.scan_alerts(store_code=payload.store_code, sku=payload.sku)
```

传递的数据包括：

```text
db          数据库会话
store_code 业务过滤条件
sku        业务过滤条件
```

API 层不关心数据库怎么查，也不关心规则怎么算。

### 12.4 Service 层 → Repository 层

Service 层调用：

```python
snapshots = self.snapshot_repo.list_inventory_snapshots(store_code=store_code, sku=sku)
```

Repository 返回：

```python
list[FactInventorySnapshot]
```

也就是库存快照 ORM 对象列表。

Service 拿到对象后，可以读取：

```python
snapshot.store_code
snapshot.sku
snapshot.available_qty
snapshot.safety_threshold
```

### 12.5 Service 层 → Calculation 层

Service 层调用：

```python
avg_daily_sales = calc_avg_daily_sales_7d(total_sales_qty)
coverage_days = calc_coverage_days(snapshot.available_qty, avg_daily_sales)
alert_result = judge_alert(snapshot, avg_daily_sales, coverage_days, days_to_expiry)
```

Calculation 层不访问数据库，只根据传入参数返回计算结果。

这让计算规则更容易测试和修改。

### 12.6 Service 层 → Repository 写入结果

Service 组装字典：

```python
alert_data = {
    "store_code": snapshot.store_code,
    "sku": snapshot.sku,
    "product_name": snapshot.product_name,
    "warning_category": alert_result["category"],
    "warning_level": alert_result["level"],
}
```

Repository 负责写入：

```python
self.alert_repo.insert_alert(alert_data)
```

Repository 把字典转成 ORM 对象：

```python
AdsInventoryAlert(**alert_data)
```

再通过 SQLAlchemy 写入数据库。

### 12.7 ORM 对象 → Pydantic Response → JSON

查询接口返回 ORM 对象列表：

```python
items = service.list_alerts(...)
return AlertListResponse(items=items)
```

Pydantic 根据响应模型转成 JSON：

```json
{
  "items": [
    {
      "id": 1,
      "store_code": "STORE001",
      "sku": 1001001,
      "product_name": "矿泉水",
      "warning_category": "缺货预警",
      "warning_level": "三级预警"
    }
  ]
}
```

这就是完整的数据传递链路。

## 13. 为什么要分这么多层

初学者可能会问：为什么不把所有代码都写在一个接口函数里？

原因是后端项目会越长越复杂。分层以后，每层职责很清楚。

| 层 | 职责 | 不应该做什么 |
| --- | --- | --- |
| API | 接收请求、校验参数、返回响应 | 不写复杂 SQL，不写业务公式 |
| Service | 编排业务流程 | 不直接拼 SQL，不处理 HTTP 细节 |
| Repository | 查询和写入数据库 | 不判断业务规则 |
| Calculation | 计算指标和规则 | 不连接数据库 |
| Model | 映射数据库表 | 不写业务流程 |
| Schema | 定义请求和响应结构 | 不查数据库 |

这样做的好处：

- 接口变多时，代码不会乱。
- 业务规则变化时，只改 `calculations`。
- 数据库查询变化时，只改 `repositories`。
- 响应字段变化时，只改 `schemas` 和少量 API。
- 后续接小程序、看板、机器人时，可以复用同一套 Service。

## 14. 5 张数据库表分别干什么

建表 SQL 在 `sql/01_schema.sql`。

| 表名 | 中文含义 | 类型 | 作用 |
| --- | --- | --- | --- |
| `dim_base_info` | 基础数据表 | 输入表 | 保存服务区、门店、摄像机基础信息 |
| `fact_pos_transaction` | 收银数据表 | 输入表 | 保存订单、门店、SKU、销售数量 |
| `fact_inventory_snapshot` | 商品库存表 | 输入表 | 保存门店 SKU 库存、补货参数、效期 |
| `ads_inventory_alert` | 库存预警结果表 | 输出表 | 保存预警扫描结果 |
| `ads_inventory_forecast` | 补货预测结果表 | 输出表 | 保存补货建议结果 |

`dim`、`fact`、`ads` 是数据仓库里常见的命名方式：

```text
dim   维度表，描述基础对象，比如门店
fact  事实表，记录业务发生的事实，比如销售、库存
ads   应用结果表，面向业务查询和应用使用
```

## 15. 怎么本地运行

安装依赖：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

配置 `.env`：

```env
APP_NAME=inventory-forecast-demo
API_PREFIX=/api/v1

POSTGRES_RECORDMANAGER_HOST=127.0.0.1
POSTGRES_RECORDMANAGER_PORT=5432
POSTGRES_RECORDMANAGER_DATABASE=inventory_forecast_demo
POSTGRES_RECORDMANAGER_USER=postgres
POSTGRES_RECORDMANAGER_PASSWORD=your_password
```

创建数据库：

```bash
createdb -h 127.0.0.1 -p 5432 -U postgres inventory_forecast_demo
```

初始化表结构和演示数据：

```bash
psql -h 127.0.0.1 -p 5432 -U postgres -d inventory_forecast_demo -f sql/01_schema.sql
psql -h 127.0.0.1 -p 5432 -U postgres -d inventory_forecast_demo -f sql/02_seed_demo_data.sql
```

启动服务：

```bash
uvicorn app.main:app --reload --port 8000
```

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

触发补货预测：

```bash
curl -X POST http://localhost:8000/api/v1/forecasts/calculate \
  -H "Content-Type: application/json" \
  -d '{}'
```

查询补货预测结果：

```bash
curl http://localhost:8000/api/v1/forecasts
```

## 16. 常见报错怎么理解

### 16.1 `GET /favicon.ico 404 Not Found`

这是浏览器自动请求网页图标。

项目没有配置 favicon，所以返回 404。

这不是业务问题，可以忽略。

### 16.2 `GET /api/v1/alerts/scan 405 Method Not Allowed`

原因是 `/api/v1/alerts/scan` 只支持 `POST`。

浏览器地址栏默认发的是 `GET` 请求，所以会返回 405。

正确调用方式：

```bash
curl -X POST http://localhost:8000/api/v1/alerts/scan \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 16.3 `500 Internal Server Error`

如果日志里出现：

```text
sqlalchemy.exc.OperationalError
connection failed
```

一般说明数据库没连上。

优先检查：

```text
1. PostgreSQL 是否启动
2. 端口是否正确，比如 5432 或 5433
3. `.env` 里的用户名密码是否正确
4. 数据库名是否存在
5. 表结构是否已经初始化
```

可以用这个命令检查数据库端口：

```bash
pg_isready -h 127.0.0.1 -p 5432
```

如果你的 PostgreSQL 实际监听的是 `5433`，`.env` 里也要改成：

```env
POSTGRES_RECORDMANAGER_PORT=5433
```

## 17. 给领导汇报时怎么讲

你可以按下面这段话讲：

```text
这个 Demo 是库存预警和补货预测的后端验证项目。
技术上使用 FastAPI 提供 API，SQLAlchemy 连接 PostgreSQL，Pydantic 做请求和响应校验。
项目按 API、Service、Repository、Calculation、Model、Schema 分层。
API 层只接收请求，Service 层编排业务流程，Repository 层读写数据库，Calculation 层负责库存覆盖天数、效期、补货缺口等规则计算。

目前已经实现 5 个接口：
健康检查、触发库存预警、查询预警结果、触发补货预测、查询预测结果。

业务上已经跑通从库存快照和收银销量出发，计算库存风险，再生成补货建议并落库的闭环。
后续可以在这个后端基础上继续接小程序、经营看板、定时任务或智能问答。
```

## 18. 新手读代码建议

建议按这个顺序读代码：

```text
1. app/main.py
2. app/api/v1/router.py
3. app/api/v1/alert_api.py
4. app/schemas/alert_schema.py
5. app/services/alert_service.py
6. app/repositories/inventory_snapshot_repo.py
7. app/repositories/pos_transaction_repo.py
8. app/core/indicator_calculator.py
9. app/core/alert_rule.py
10. app/repositories/inventory_alert_repo.py
11. app/api/v1/forecast_api.py
12. app/services/forecast_service.py
13. app/core/forecast_rule.py
14. app/mappers/fact_inventory_snapshot.py
15. sql/01_schema.sql
```

不要一开始就从所有文件一起看。先顺着一个接口请求走完，你会更容易理解整个后端项目。
