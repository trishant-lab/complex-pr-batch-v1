from dataclasses import dataclass
from uuid import UUID

from app.cli.temporal.core.base import IODataclass

ProductName: str = "veritable"
OnepasswordVaultName: str = "practifly"
OnepasswordItemName: str = "veritable-tenant-config-{environment}"


@dataclass
class ResourceSpec:
    """
    ResourceSpec dataclass
    """
    request_memory: str
    request_cpu: str
    limit_memory: str
    limit_cpu: str


@dataclass
class VeritableCustomerDetails(IODataclass):
    """
    VeritableCustomerDetails dataclass
    """
    customerId: UUID
    customerUserName: str
    customerEmail: str
    customerRealmRoles: list[str]
    orgName: str


@dataclass
class VeritableSpec(IODataclass):
    """
    VeritableSpec dataclass
    """
    tenant: str
    imageTag: None | str = None
    customerDetails: None | VeritableCustomerDetails = None
    serverSpec: None | ResourceSpec = None
    cliSpec: None | ResourceSpec = None
