from fastapi import APIRouter

from app.schemas.common import HealthResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """健康检查接口，用于快速确认服务进程可响应请求。"""
    return HealthResponse(status="ok")
