from app.models.lago.base_model import BaseResponseModel, LagoBaseModel
from app.models.lago.credit import CreditsResponse


class AppliedCoupon(LagoBaseModel):
    external_customer_id: str
    coupon_code: str
    amount_cents: int | None = None
    amount_currency: str | None = None
    percentage_rate: float | None = None
    frequency: str | None = None
    frequency_duration: int | None = None


class AppliedCouponResponse(BaseResponseModel):
    lago_id: str
    lago_coupon_id: str
    coupon_code: str
    status: str | None = None
    external_customer_id: str
    lago_customer_id: str
    amount_cents: int | None = None
    amount_cents_remaining: int | None = None
    amount_currency: str | None = None
    expiration_at: str | None = None
    created_at: str
    terminated_at: str | None = None
    percentage_rate: float | None = None
    frequency: str | None = None
    frequency_duration: int | None = None
    frequency_duration_remaining: int | None = None
    credits: CreditsResponse | None = None
