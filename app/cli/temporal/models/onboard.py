from datetime import datetime
from enum import IntEnum
from typing import Any
from uuid import UUID

from pydantic import Field

from app.cli.temporal.core.base import LaunchpadCLIBaseModel
from app.models.lago.invoice import InvoiceResponse
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum


class CustomerWorkflowInput(LaunchpadCLIBaseModel):
    customer_id: UUID = Field(frozen=True)
    product: ProductEnum = Field(frozen=True)


class OnboardWorkflowStatus(IntEnum):
    NOT_STARTED = 0
    STARTED = 1
    SUBSCRIPTION_CREATION = 2
    CHARGE_CREATION = 3
    PAYMENT_FAILURE = 4
    CREATING_ENVIRONMENT = 5
    SENDING_MAIL = 6
    COMPLETED = 7


class OnboardInfo(CustomerWorkflowInput):
    tenant_name: str = Field(frozen=True)
    subscription_id: UUID = Field(frozen=True)
    subscription_plan: str = Field(frozen=True)
    subscription_created: datetime = Field(frozen=True)
    failed_invoice_id: str | None = Field(None)
    invoice: InvoiceResponse | None = Field(None)
    failed_invoice_reason: dict[str, Any] | None = Field(None)
    onboard_status: TenantStatusEnum = Field(default=TenantStatusEnum.NotApplicable)
    workflow_status: OnboardWorkflowStatus = Field(default=OnboardWorkflowStatus.NOT_STARTED)
