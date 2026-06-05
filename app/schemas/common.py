from decimal import Decimal

from pydantic import BaseModel, ConfigDict


def serialize_decimal(value: Decimal) -> int | float:
    if value == value.to_integral_value():
        return int(value)
    return float(value)


class AppBaseModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={Decimal: serialize_decimal},
    )


class HealthResponse(AppBaseModel):
    status: str
