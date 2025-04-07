from app.models.lago.base_model import BaseListResponseModel, BaseResponseModel, LagoBaseModel
from app.models.lago.credit import CreditsResponse
from app.models.lago.customer import CustomerResponse
from app.models.lago.error_details import ErrorDetailsResponse
from app.models.lago.fee import FeesResponse
from app.models.lago.subscription import SubscriptionsResponse
from app.models.lago.usage_threshold import UsageThreshold


class InvoicePaymentStatusChange(LagoBaseModel):
    payment_status: str


class InvoiceMetadata(LagoBaseModel):
    id: str | None = None
    key: str | None = None
    value: str | None = None


class InvoiceFee(LagoBaseModel):
    add_on_code: str | None = None
    unit_amount_cents: int | None = None
    units: float | None = None
    description: str | None = None
    invoice_display_name: str | None = None
    tax_codes: list[str] | None = None


class InvoiceMetadataList(BaseListResponseModel[InvoiceMetadata]):
    root: list[InvoiceMetadata]


class InvoiceFeesList(BaseListResponseModel[InvoiceFee]):
    root: list[InvoiceFee]


class Invoice(LagoBaseModel):
    payment_status: str | None = None
    metadata: InvoiceMetadataList | None = None


class OneOffInvoice(LagoBaseModel):
    external_customer_id: str | None = None
    currency: str | None = None
    fees: InvoiceFeesList | None = None
    error_details: ErrorDetailsResponse | None = None


class InvoiceAppliedTax(BaseResponseModel):
    lago_id: str | None = None
    lago_invoice_id: str | None = None
    lago_tax_id: str | None = None
    tax_name: str | None = None
    tax_code: str | None = None
    tax_rate: float | None = None
    tax_description: str | None = None
    amount_cents: int | None = None
    amount_currency: str | None = None
    fees_amount_cents: int | None = None
    created_at: str | None = None


class InvoiceAppliedTaxes(BaseListResponseModel[InvoiceAppliedTax]):
    root: list[InvoiceAppliedTax]


class InvoiceAppliedUsageThreshold(BaseResponseModel):
    lifetime_usage_amount_cents: int | None = None
    created_at: str | None = None
    usage_threshold: UsageThreshold | None = None


class InvoiceAppliedUsageThresholds(BaseListResponseModel[InvoiceAppliedUsageThreshold]):
    root: list[InvoiceAppliedUsageThreshold]


class InvoiceResponse(LagoBaseModel):
    lago_id: str
    sequential_id: int | None = None
    number: str
    issuing_date: str | None = None
    payment_dispute_lost_at: str | None = None
    payment_due_date: str | None = None
    payment_overdue: bool
    net_payment_term: int
    invoice_type: str
    version_number: int
    status: str
    payment_status: str
    currency: str
    fees_amount_cents: int
    coupons_amount_cents: int
    taxes_amount_cents: int
    credit_notes_amount_cents: int
    progressive_billing_credit_amount_cents: int
    sub_total_excluding_taxes_amount_cents: int
    sub_total_including_taxes_amount_cents: int
    total_amount_cents: int
    total_due_amount_cents: int
    prepaid_credit_amount_cents: int

    file_url: str | None = None
    customer: CustomerResponse | None = None
    subscriptions: SubscriptionsResponse | None = None
    fees: FeesResponse | None = None
    credits: CreditsResponse | None = None
    metadata: InvoiceMetadataList | None = None
    applied_taxes: InvoiceAppliedTaxes | None = None
    applied_usage_thresholds: InvoiceAppliedUsageThresholds | None = None
    error_details: ErrorDetailsResponse | None = None
