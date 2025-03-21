from app.models.lago.base_model import LagoBaseModel
from app.models.lago.tax import TaxesResponse


class MinimumCommitmentResponse(LagoBaseModel):
    lago_id: str
    amount_cents: int
    invoice_display_name: str | None = None
    interval: str
    taxes: TaxesResponse | None = None
    created_at: str | None = None
    updated_at: str | None = None


class MinimumCommitmentOverrides(LagoBaseModel):
    amount_cents: int | None = None
    invoice_display_name: str | None = None
    tax_codes: list[str] | None = None
