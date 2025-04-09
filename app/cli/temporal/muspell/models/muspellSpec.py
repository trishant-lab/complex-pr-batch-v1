from app.cli.temporal.core.base import LaunchpadCLIBaseModel
from app.cli.temporal.models.base_spec import BaseResourceSpec, BaseSpec


class ResourceSpec(LaunchpadCLIBaseModel):
    """
    ResourceSpec dataclass
    """

    request_memory: str = "500Mi"
    request_cpu: str = "100m"
    limit_memory: str = "3000Mi"
    limit_cpu: str = "3000m"


class CustomerDetails(BaseResourceSpec):
    """
    CustomerDetails dataclass
    """


class MuspellArchiveSpec(BaseSpec):
    """
    MuspellArchiveSpec dataclass
    """

    emailSent: bool = False
    serverSpec: None | ResourceSpec = ResourceSpec()
