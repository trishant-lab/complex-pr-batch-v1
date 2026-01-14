from typing import Annotated
from pydantic import StringConstraints, field_validator
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
    whichEhrDoesYourCompanyUse: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    spaceDisplayName: str
    emailSent: bool = False
    is_deployment: bool = False
    organization: str | None = None
    customerDomain: str | None = None
    serverSpec: ResourceSpec | None = ResourceSpec()
    cliSpec: ResourceSpec | None = ResourceSpec()
    spaceDisplayName: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None

    @field_validator("whichEhrDoesYourCompanyUse")
    @classmethod
    def lowercase_ehr(cls, v: str) -> str:
        """
        Lowercase the EHR
        """
        return v.lower()


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
    spaceDisplayName: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

    @field_validator("ehr")
    @classmethod
    def lowercase_ehr(cls, v: str) -> str:
        """
        Lowercase the EHR
        """
        return v.lower()
