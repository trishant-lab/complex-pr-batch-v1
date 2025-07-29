from app.cli.temporal.models.base_spec import BaseResourceSpec, BaseSpec


class ResourceSpec(BaseResourceSpec):
    """
    ResourceSpec dataclass
    """

    limit_memory: str = "5000Mi"


class PricedxSpec(BaseSpec):
    """
    PricedxSpec dataclass
    """

    emailSent: bool = False
    isDeployment: bool = False
    isConsole: bool = False
    organization: str | None = None
    serverSpec: ResourceSpec | None = ResourceSpec()
    cliSpec: ResourceSpec | None = ResourceSpec()
