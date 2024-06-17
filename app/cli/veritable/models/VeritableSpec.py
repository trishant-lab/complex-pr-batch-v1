from uuid import UUID

from app.cli.temporal.core.base import LaunchpadCLIBaseModel


class ResourceSpec(LaunchpadCLIBaseModel):
    """
    ResourceSpec dataclass
    """

    request_memory: str = "500Mi"
    request_cpu: str = "500m"
    limit_memory: str = "3000Mi"
    limit_cpu: str = "3000m"


class VeritableCustomerDetails(LaunchpadCLIBaseModel):
    """
    VeritableCustomerDetails dataclass
    """

    customerId: UUID
    userName: str
    email: str
    organization: str


class VeritableSpec(LaunchpadCLIBaseModel):
    """
    VeritableSpec dataclass
    """

    tenant: str
    imageTag: None | str = None
    customerDetails: None | VeritableCustomerDetails = None
    serverSpec: None | ResourceSpec = ResourceSpec()
    cliSpec: None | ResourceSpec = ResourceSpec()
