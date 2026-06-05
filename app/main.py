from fastapi import FastAPI

from app.api.v1.router import api_router
from app.config.config import settings


app = FastAPI(title=settings.app_name)
# 所有业务接口统一挂载在配置的 API 前缀下，便于后续版本化。
app.include_router(api_router, prefix=settings.api_prefix)
