from datetime import datetime
from enum import IntEnum
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.core.ijson import ijson_loads
from app.models.product import ProductEnum


class TenantStatusEnum(IntEnum):
    NotApplicable = -2
    Stale = 0
    ApprovalPending = 3
    ApprovalDeclined = -3
    Approved = 4
    Provisioning = 1
    ProvisioningFailed = -1
    Provisioned = 2
    DeProvisioning = 5
    DeProvisioned = 6
    DeprovisioningFailed = -4

    @classmethod
    def can_update_tenant(cls, status: "TenantStatusEnum") -> bool:
        """
        Returns True if the tenant details can be updated
        """
        return status in [cls.Declined, cls.NotApplicable, cls.Stale, cls.PendingApproval]


class TenantCreateRequestModel(BaseModel):
    tenantname: str
    email: EmailStr
    product: ProductEnum
    formSchema: str
    status: TenantStatusEnum
    orgname: str | None = None
    source: str | None = None
    approvedBy: str | None = None
    formData: str


class TenantResponseModel(BaseModel):
    id: UUID
    name: str
    status: TenantStatusEnum
    orgname: str | None = None
    email: EmailStr | None = None
    source: str | None = None
    formSchema: list[dict] | None = None
    formData: dict | None = None
    approvedBy: UUID | None = None
    created: datetime
    provisionedDateTime: datetime | None = None

    @classmethod
    def json_to_model(cls, value: dict) -> "TenantResponseModel":
        """
        Convert db response to model
        """
        value["formData"] = ijson_loads(value["data"]) if value.get("data") else None
        value["formSchema"] = ijson_loads(value["schema"]) if value.get("schema") else None
        value["name"] = value.get("tenantname")
        return cls(**value)


class SuggestTenantNamesResponseModel(BaseModel):
    tenant_names: list[str]
    domain: str
