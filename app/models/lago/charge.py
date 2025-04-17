from typing import Any

from app.models.lago.base_model import BaseListResponseModel, BaseResponseModel, LagoBaseModel
from app.models.lago.tax import TaxesResponse


class ChargeFilter(LagoBaseModel):
    invoice_display_name: str | None = None
    properties: dict[str, Any] | None = None
    values: dict[str, list[str]] | None = None


class ChargeFilters(BaseListResponseModel[ChargeFilter]):
    root: list[ChargeFilter]


class ChargeResponse(BaseResponseModel):
    lago_id: str | None = None
    lago_billable_metric_id: str | None = None
    billable_metric_code: str | None = None
    charge_model: str | None = None
    pay_in_advance: bool | None = None
    prorated: bool | None = None
    invoiceable: bool | None = None
    regroup_paid_fees: str | None = None
    invoice_display_name: str | None = None
    min_amount_cents: int | None = None
    properties: dict[str, Any] | None = None
    filters: ChargeFilters | None = None
    taxes: TaxesResponse | None = None


class ChargesResponse(BaseListResponseModel[ChargeResponse]):
    root: list[ChargeResponse]


class ChargeOverrides(LagoBaseModel):
    id: str | None = None
    invoice_display_name: str | None = None
    min_amount_cents: int | None = None
    properties: dict[str, Any] | None = None
    filters: ChargeFilters | None = None
    tax_codes: list[str] | None = None


class ChargesOverrides(BaseListResponseModel[ChargeOverrides]):
    root: list[ChargeOverrides]
