from typing import Any

from app.models.lago.base_model import BaseListResponseModel, BaseResponseModel, LagoBaseModel
from app.models.lago.invoice_item import InvoiceItemResponse


class Fee(LagoBaseModel):
    payment_status: str | None = None
    invoice_display_name: str | None = None


class FeeAppliedTax(BaseResponseModel):
    lago_id: str | None = None
    lago_fee_id: str | None = None
    lago_tax_id: str | None = None
    tax_name: str | None = None
    tax_code: str | None = None
    tax_rate: float | None = None
    tax_description: str | None = None
    amount_cents: int | None = None
    amount_currency: str | None = None
    created_at: str | None = None


class FeeAppliedTaxes(BaseListResponseModel[FeeAppliedTax]):
    root: list[FeeAppliedTax]


class PricingUnitDetails(BaseResponseModel):
    lago_pricing_unit_id: str | None = None
    pricing_unit_code: str | None = None
    short_name: str | None = None
    amount_cents: int | None = None
    precise_amount_cents: str | None = None
    unit_amount_cents: int | None = None
    precise_unit_amount: str | None = None
    conversion_rate: float | None = None


class FeeResponse(BaseResponseModel):
    lago_id: str | None = None
    lago_charge_id: str | None = None
    lago_charge_filter_id: str | None = None
    lago_invoice_id: str | None = None
    lago_true_up_fee_id: str | None = None
    lago_true_up_parent_fee_id: str | None = None
    external_subscription_id: str | None = None
    amount_cents: int | None = None
    amount_currency: str | None = None
    taxes_amount_cents: int | None = None
    taxes_rate: float | None = None
    total_amount_cents: int | None = None
    unit_amount_cents: int | None = None  # deprecated
    precise_unit_amount: str | None = None
    precise_amount: str | None = None
    precise_total_amount: str | None = None
    taxes_precise_amount: str | None = None
    total_amount_currency: str | None = None
    units: str | None = None
    total_aggregated_units: str | None = None
    events_count: int | None = None
    payment_status: str | None = None
    created_at: str | None = None
    description: str | None = None
    pay_in_advance: bool | None = None
    invoiceable: bool | None = None
    invoice_display_name: str | None = None
    succeeded_at: str | None = None
    failed_at: str | None = None
    refunded_at: str | None = None
    from_date: str | None = None
    to_date: str | None = None
    amount_details: dict[str, Any] | None = None
    pricing_unit_details: PricingUnitDetails | None = None
    billing_entity_code: str | None = None

    item: InvoiceItemResponse | None = None
    applied_taxes: FeeAppliedTaxes | None = None


class FeesResponse(BaseListResponseModel[FeeResponse]):
    root: list[FeeResponse]
