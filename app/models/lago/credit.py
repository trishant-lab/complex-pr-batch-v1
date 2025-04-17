from app.models.lago.base_model import BaseListResponseModel, BaseResponseModel, LagoBaseModel
from app.models.lago.invoice_item import InvoiceItemResponse


class InvoiceShortDetails(LagoBaseModel):
    lago_id: str | None = None
    payment_status: str | None = None


class CreditResponse(BaseResponseModel):
    lago_id: str | None = None
    amount_cents: int | None = None
    amount_currency: str | None = None
    before_taxes: bool
    item: InvoiceItemResponse | None = None
    invoice: InvoiceShortDetails | None = None


class CreditsResponse(BaseListResponseModel[CreditResponse]):
    root: list[CreditResponse]
