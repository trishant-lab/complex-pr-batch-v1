from dataclasses import dataclass


class ResourceSpec:
    """
    ResourceSpec dataclass
    """
    request_memory: str = "500Mi"
    request_cpu: str = "500m"
    limit_memory: str = "3000Mi"
    limit_cpu: str = "3000m"


@dataclass
class VeritableSpec:
    """
    VeritableSpec dataclass
    """
    tenant: str
    imageTag: str
    newImageTag: str
    environment: str
    customerId: str
    customerUserName: str
    customerEmail: str
    customerRealmRoles: list[str]
    orgName: str
    serverSpec: ResourceSpec = ResourceSpec()
    cliSpec: ResourceSpec = ResourceSpec()
