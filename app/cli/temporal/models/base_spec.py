from app.cli.temporal.core.base import LaunchpadCLIBaseModel


class BaseResourceSpec(LaunchpadCLIBaseModel):
    """
    ResourceSpec dataclass
    """

    request_memory: str = "500Mi"
    request_cpu: str = "100m"
    limit_memory: str = "3000Mi"
    limit_cpu: str = "3000m"


class BaseSpec(LaunchpadCLIBaseModel):
    """
    BaseSpec dataclass
    """

    tenant: str
    firstName: str
    lastName: str
    email: str
    organization: str
    serverSpec: None | BaseResourceSpec = BaseResourceSpec()
