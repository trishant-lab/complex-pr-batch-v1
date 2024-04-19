from dataclasses import dataclass
from uuid import UUID


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
class VeritableSpec:
    """
    VeritableSpec dataclass
    """
    tenant: str
    imageTag: str
    environment: str
    customerId: UUID
    customerUserName: str
    customerEmail: str
    customerRealmRoles: list[str]
    orgName: str
    serverSpec: ResourceSpec
    cliSpec: ResourceSpec
