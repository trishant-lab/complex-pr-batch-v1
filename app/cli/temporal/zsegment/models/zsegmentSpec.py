from app.cli.temporal.core.base import LaunchpadCLIBaseModel


class ResourceSpec(LaunchpadCLIBaseModel):
    """
    ResourceSpec dataclass
    """

    request_memory: str = "500Mi"
    request_cpu: str = "500m"
    limit_memory: str = "3000Mi"
    limit_cpu: str = "3000m"


class CustomerDetails(LaunchpadCLIBaseModel):
    """
    CustomerDetails dataclass
    """


class ZSegmentSpec(LaunchpadCLIBaseModel):
    """
    ZSegmentSpec dataclass
    """

    tenant: str
    firstName: str
    lastName: str
    email: str
    organization: None | str = None
    emailSent: bool = False
    serverSpec: None | ResourceSpec = ResourceSpec()
    kestraSpec: None | ResourceSpec = ResourceSpec()
    PlanName: str = "Free"
