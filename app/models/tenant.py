import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class TenantStatusEnum(str, Enum):
    PendingApproval = "PendingApproval"
    Approved = "Approved"
    Declined = "Declined"
    Provisioning = "Provisioning"
    Completed = "Completed"
    Failed = "Failed"
    DeProvisioning = "DeProvisioning"
    DeProvisioned = "DeProvisioned"


class TenantCreateRequestModel(BaseModel):
    name: str
    product: uuid.UUID
    status: TenantStatusEnum
    source: None | str = None
    requestor: dict
    approvedBy: None | str = None


class RequestorModel(BaseModel):
    id: str
    username: str
    email: str
    organization: str


class TenantResponseModel(BaseModel):
    id: uuid.UUID
    name: str
    status: TenantStatusEnum
    source: None | str = None
    requestor: RequestorModel
    approvedBy: None | str = None
    created: datetime
    provisionedDateTime: None | datetime = None


class UpdateRequestorModel(BaseModel):
    tenant_id: uuid.UUID
    username: str
    email: str
    organization: str
