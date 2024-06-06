from dataclasses import dataclass, field
from uuid import UUID

from app.cli.temporal.core.base import IODataclass

OnepasswordVaultName: str = "dexit"
OnepasswordItemName: str = "dexit-tenant-config-{environment}"


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
class CustomerDetails(IODataclass):
    """
    CustomerDetails dataclass
    """
    userName: str
    email: str
    organization: str


@dataclass
class DexitSpec(IODataclass):
    """
    DexitSpec dataclass
    """
    tenant: str
    customerDetails: None | CustomerDetails = None
    imageTag: None | str = None
    serverSpec: None | ResourceSpec = field(default_factory=ResourceSpec)
    cliSpec: None | ResourceSpec = field(default_factory=ResourceSpec)
