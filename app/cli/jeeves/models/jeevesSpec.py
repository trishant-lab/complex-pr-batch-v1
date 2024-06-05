import dataclasses

from app.cli.temporal.core.base import IODataclass


@dataclasses.dataclass
class ResourceSpec:
    """
    ResourceSpec dataclass
    """
    request_memory: str = "500m"
    request_cpu: str = "500Mi"
    limit_memory: str = "3000m"
    limit_cpu: str = "3000Mi"


@dataclasses.dataclass
class CustomerDetails(IODataclass):
    """
    CustomerDetails dataclass
    """
    userName: str
    email: str
    organization: str


@dataclasses.dataclass
class JeevesSpec(IODataclass):
    """
    JeevesSpec dataclass
    """
    tenant: str
    customerDetails: None | CustomerDetails = None
    serverSpec: None | ResourceSpec = dataclasses.field(default_factory=ResourceSpec)
    cliSpec: None | ResourceSpec = dataclasses.field(default_factory=ResourceSpec)
