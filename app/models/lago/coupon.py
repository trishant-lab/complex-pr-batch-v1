from typing import Any

from app.models.lago.base_model import BaseResponseModel


class CouponResponse(BaseResponseModel):
    lago_id: str
    name: str
    code: str
    description: str | None = None
    amount_cents: int | None = None
    amount_currency: str | None = None
    created_at: str
    expiration: str
    expiration_at: str | None = None
    terminated_at: str | None = None
    percentage_rate: float | None = None
    coupon_type: str | None = None
    reusable: bool | None = None
    frequency: str | None = None
    frequency_duration: int | None = None
    plan_codes: list[Any] | None = None
    limited_plans: bool | None = None
    billable_metric_codes: list[Any] | None = None
    limited_billable_metrics: bool | None = None
