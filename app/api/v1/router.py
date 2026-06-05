from fastapi import APIRouter

from app.api.v1.alert_api import router as alert_router
from app.api.v1.forecast_api import router as forecast_router
from app.api.v1.health_api import router as health_router


api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(alert_router, prefix="/alerts", tags=["alerts"])
api_router.include_router(forecast_router, prefix="/forecasts", tags=["forecasts"])
