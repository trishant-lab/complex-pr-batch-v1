from app.cli.temporal.core.base import LaunchpadCLIBaseModel


class ResourceSpec(LaunchpadCLIBaseModel):
    """
    ResourceSpec dataclass
    """

    request_memory: str = "500Mi"
    request_cpu: str = "500m"
    limit_memory: str = "3000Mi"
    limit_cpu: str = "3000m"


class VeritableSpec(LaunchpadCLIBaseModel):
    """
    VeritableSpec dataclass
    """

    tenant: str
    customerId: str
    firstName: str
    lastName: str
    email: str
    orgName: str
    emailSent: bool = False
    serverSpec: None | ResourceSpec = ResourceSpec()
    cliSpec: None | ResourceSpec = ResourceSpec()
