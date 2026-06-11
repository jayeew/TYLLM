from fastapi import APIRouter

from app.api.v1.alert_api import router as alert_router
from app.api.v1.forecast_api import router as forecast_router
from app.api.v1.health_api import router as health_router
from app.api.v1.product_api import router as product_router


api_router = APIRouter()
# 聚合 v1 版本下的所有子路由，保持入口文件只关心统一前缀。
api_router.include_router(health_router, tags=["health"])
api_router.include_router(alert_router, prefix="/alerts", tags=["alerts"])
api_router.include_router(forecast_router, prefix="/forecasts", tags=["forecasts"])
api_router.include_router(product_router, prefix="/products", tags=["products"])
