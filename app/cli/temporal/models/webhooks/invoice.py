from enum import EnumMeta, StrEnum

from pydantic import Field

from app.cli.temporal.core.base import LaunchpadCLIBaseModel
from app.models.lago.invoice import InvoiceResponse
from app.models.product import ProductEnum


class ProviderError(LaunchpadCLIBaseModel):
    message: str | None = Field(None, description="Error message from the provider")
    error_code: str | None = Field(None, description="Error code provided by the provider")


class PaymentProviderInvoicePaymentError(LaunchpadCLIBaseModel):
    lago_invoice_id: str | None = Field(None, description="Unique identifier for the Lago invoice")
    lago_customer_id: str | None = Field(None, description="Unique identifier for the Lago customer")
    external_customer_id: str | None = Field(None, description="External identifier for the customer")
    provider_customer_id: str | None = Field(None, description="Customer identifier in the payment provider's system")
    payment_provider: str | None = Field(None, description="Name of the payment provider")
    provider_error: ProviderError = Field(..., description="Details of the error provided by the payment provider")


class InvoiceWebhookEvent(LaunchpadCLIBaseModel):
    product: ProductEnum = Field(frozen=True)
    webhook_type: str = Field(frozen=True)
    object_type: str = Field(frozen=True)
    invoice: InvoiceResponse | None = Field(None, frozen=True)
    payment_provider_invoice_payment_error: PaymentProviderInvoicePaymentError | None = Field(None, frozen=True)


class StrValEnum(EnumMeta):
    def __contains__(cls: type["StrValEnum"], item: str) -> bool:
        """
        :param item:
        :return:
        """
        try:
            cls(item)
        except ValueError:
            return False
        return True


class InvoiceWebhookType(StrEnum, metaclass=StrValEnum):
    created = "invoice.created"
    payment_status_updated = "invoice.payment_status_updated"
    payment_failure = "invoice.payment_failure"
