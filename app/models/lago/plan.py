from app.models.lago.base_model import BaseResponseModel, LagoBaseModel
from app.models.lago.charge import ChargesOverrides, ChargesResponse
from app.models.lago.minimum_commitment import MinimumCommitmentOverrides, MinimumCommitmentResponse
from app.models.lago.tax import TaxesResponse
from app.models.lago.usage_threshold import UsageThresholdsOverrides, UsageThresholdsResponse


class PlanResponse(BaseResponseModel):
    lago_id: str
    name: str
    invoice_display_name: str | None = None
    created_at: str
    code: str
    interval: str | None = None
    description: str | None = None
    amount_cents: int | None = None
    amount_currency: str | None = None
    trial_period: float | None = None
    pay_in_advance: bool | None = None
    bill_charges_monthly: bool | None = None
    charges: ChargesResponse | None = None
    minimum_commitment: MinimumCommitmentResponse | None = None
    usage_thresholds: UsageThresholdsResponse | None = None
    active_subscriptions_count: int | None = None
    draft_invoices_count: int | None = None
    taxes: TaxesResponse | None = None


class PlanOverrides(LagoBaseModel):
    name: str | None = None
    invoice_display_name: str | None = None
    description: str | None = None
    amount_cents: int | None = None
    amount_currency: str | None = None
    trial_period: float | None = None
    charges: ChargesOverrides | None = None
    minimum_commitment: MinimumCommitmentOverrides | None = None
    usage_thresholds: UsageThresholdsOverrides | None = None
    tax_codes: list[str] | None = None
