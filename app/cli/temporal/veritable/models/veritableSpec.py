from app.cli.temporal.core.base import LaunchpadCLIBaseModel
import uuid


class ResourceSpec(LaunchpadCLIBaseModel):
    """
    ResourceSpec dataclass
    """

    request_memory: str = "500Mi"
    request_cpu: str = "100m"
    limit_memory: str = "3000Mi"
    limit_cpu: str = "3000m"


class VeritableSpec(LaunchpadCLIBaseModel):
    """
    VeritableSpec dataclass
    """

    tenant: str
    customer_id: str
    first_name: str
    last_name: str
    email: str
    org_name: str
    reconcile: bool = False
    emailSent: bool = False
    server_spec: None | ResourceSpec = ResourceSpec()
    cli_spec: None | ResourceSpec = ResourceSpec()
