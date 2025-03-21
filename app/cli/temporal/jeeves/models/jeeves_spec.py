from app.cli.temporal.models.base_spec import BaseResourceSpec, BaseSpec


class ResourceSpec(BaseResourceSpec):
    """
    ResourceSpec dataclass
    """

    limit_memory: str = "5000Mi"


class JeevesSpec(BaseSpec):
    """
    JeevesSpec dataclass
    """

    companyNameProvidersOrPayersOnly: str
    whichEhrDoesYourCompanyUse: str
    emailSent: bool = False
    is_deployment: bool = False
    organization: str | None = None
    serverSpec: ResourceSpec | None = ResourceSpec()
    cliSpec: ResourceSpec | None = ResourceSpec()
