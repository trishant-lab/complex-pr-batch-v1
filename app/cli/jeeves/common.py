import dataclasses

from app.cli.temporal.core.base import IODataclass

ProductName = "jeeves"


@dataclasses.dataclass
class ResourceSpec:
    """
    ResourceSpec dataclass
    """
    request_memory: str
    request_cpu: str
    limit_memory: str
    limit_cpu: str


@dataclasses.dataclass
class CustomerDetails(IODataclass):
    """
    CustomerDetails dataclass
    """
    customerUserName: str
    customerEmail: str


@dataclasses.dataclass
class JeevesSpec(IODataclass):
    """
    JeevesSpec dataclass
    """
    tenant: str
    customerDetails: None | CustomerDetails = None
    serverSpec: None | ResourceSpec = None
    cliSpec: None | ResourceSpec = None
