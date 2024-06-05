from dataclasses import dataclass, field, Field
from uuid import UUID

from app.cli.temporal.core.base import IODataclass


@dataclass
class ResourceSpec:
    """
    ResourceSpec dataclass
    """
    request_memory: str = "500m"
    request_cpu: str = "500Mi"
    limit_memory: str = "3000m"
    limit_cpu: str = "3000Mi"


@dataclass
class VeritableCustomerDetails:
    """
    VeritableCustomerDetails dataclass
    """
    customerId: UUID
    userName: str
    email: str
    organization: str


@dataclass
class VeritableSpec(IODataclass):
    """
    VeritableSpec dataclass
    """
    tenant: str
    imageTag: None | str = None
    customerDetails: None | VeritableCustomerDetails = None
    serverSpec: None | ResourceSpec = field(default_factory=ResourceSpec)
    cliSpec: None | ResourceSpec = field(default_factory=ResourceSpec)
