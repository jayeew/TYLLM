from decimal import Decimal

from pydantic import BaseModel, ConfigDict


def serialize_decimal(value: Decimal) -> int | float:
    """把 Decimal 序列化成更适合 JSON 展示的 int 或 float。"""
    if value == value.to_integral_value():
        return int(value)
    return float(value)


class AppBaseModel(BaseModel):
    """项目统一的 Pydantic 基类，开启 ORM 对象读取和 Decimal 编码。"""

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={Decimal: serialize_decimal},
    )


class HealthResponse(AppBaseModel):
    """健康检查响应。"""

    status: str
