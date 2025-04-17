from app.models.lago.base_model import BaseResponseModel


class InvoiceItemResponse(BaseResponseModel):
    type: str | None = None
    code: str | None = None
    name: str | None = None
    invoice_display_name: str | None = None
    filter_invoice_display_name: str | None = None
    filters: dict[str, list[str]] | None = None
    lago_item_id: str | None = None
    item_type: str | None = None
    grouped_by: dict[str, str] | None = None
