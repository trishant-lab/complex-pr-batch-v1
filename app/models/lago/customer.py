from app.models.lago.base_model import BaseListResponseModel, BaseResponseModel, LagoBaseModel
from app.models.lago.tax import TaxesResponse


class CustomerBillingConfiguration(LagoBaseModel):
    invoice_grace_period: int | None = None
    subscription_invoice_issuing_date_anchor: str | None = None
    subscription_invoice_issuing_date_adjustment: str | None = None
    payment_provider: str | None = None
    payment_provider_code: str | None = None
    provider_customer_id: str | None = None
    sync: bool | None = None
    sync_with_provider: bool | None = None
    document_locale: str | None = None
    provider_payment_methods: list[str] | None = None


class Address(LagoBaseModel):
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    zipcode: str | None = None
    state: str | None = None
    country: str | None = None


class IntegrationCustomer(LagoBaseModel):
    id: str | None = None
    external_customer_id: str | None = None
    integration_type: str | None = None
    integration_code: str | None = None
    subsidiary_id: str | None = None
    sync_with_provider: bool | None = None


class IntegrationCustomerResponse(LagoBaseModel):
    lago_id: str | None = None
    external_customer_id: str | None = None
    type: str | None = None
    integration_code: str | None = None
    subsidiary_id: str | None = None
    sync_with_provider: bool | None = None


class IntegrationCustomersList(BaseListResponseModel[IntegrationCustomer]):
    root: list[IntegrationCustomer]


class IntegrationCustomersResponseList(BaseListResponseModel[IntegrationCustomerResponse]):
    root: list[IntegrationCustomerResponse]


class Metadata(LagoBaseModel):
    id: str | None = None
    key: str | None = None
    value: str | None = None
    display_in_invoice: bool | None = None


class MetadataResponse(LagoBaseModel):
    lago_id: str | None = None
    key: str | None = None
    value: str | None = None
    display_in_invoice: bool | None = None


class MetadataList(BaseListResponseModel[Metadata]):
    root: list[Metadata]


class MetadataResponseList(BaseListResponseModel[MetadataResponse]):
    root: list[MetadataResponse]


class Customer(LagoBaseModel):
    external_id: str
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    country: str | None = None
    currency: str | None = None
    email: str | None = None
    legal_name: str | None = None
    legal_number: str | None = None
    net_payment_term: int | None = None
    tax_identification_number: str | None = None
    logo_url: str | None = None
    name: str | None = None
    firstname: str | None = None
    lastname: str | None = None
    customer_type: str | None = None
    phone: str | None = None
    state: str | None = None
    timezone: str | None = None
    url: str | None = None
    zipcode: str | None = None
    metadata: MetadataList | None = None
    finalize_zero_amount_invoice: str | None = None
    billing_configuration: CustomerBillingConfiguration | None = None
    shipping_address: Address | None = None
    integration_customers: IntegrationCustomersList | None = None
    tax_codes: list[str] | None = None


class CustomerResponse(BaseResponseModel):
    lago_id: str
    external_id: str
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    country: str | None = None
    currency: str | None = None
    email: str | None = None
    created_at: str
    updated_at: str
    legal_name: str | None = None
    legal_number: str | None = None
    net_payment_term: int | None = None
    tax_identification_number: str | None = None
    logo_url: str | None = None
    name: str | None = None
    firstname: str | None = None
    lastname: str | None = None
    customer_type: str | None = None
    phone: str | None = None
    state: str | None = None
    timezone: str | None = None
    applicable_timezone: str
    url: str | None = None
    zipcode: str | None = None
    metadata: MetadataResponseList | None = None
    finalize_zero_amount_invoice: str | None = None
    billing_configuration: CustomerBillingConfiguration | None = None
    shipping_address: Address | None = None
    integration_customers: IntegrationCustomersResponseList | None = None
    taxes: TaxesResponse | None = None
