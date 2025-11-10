from typing import Annotated
from pydantic import StringConstraints
from app.cli.temporal.models.base_spec import BaseResourceSpec, BaseSpec
from app.cli.temporal.core.base import LaunchpadCLIBaseModel


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
    customerDomain: str | None = None
    serverSpec: ResourceSpec | None = ResourceSpec()
    cliSpec: ResourceSpec | None = ResourceSpec()


class SpaceSpec(LaunchpadCLIBaseModel):
    """
    SpaceSpec dataclass
    """

    space: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    tenant: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    ehr: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    firstName: str
    lastName: str
