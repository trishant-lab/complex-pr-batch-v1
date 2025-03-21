from enum import Enum

from app.cli.temporal.core.base import LaunchpadCLIBaseModel
from app.cli.temporal.models.base_spec import BaseResourceSpec, BaseSpec


class TenantType(str, Enum):
    staffing = "Staffing"
    internalhiring = "InternalHiring"

    @classmethod
    def get_tenant_type(cls: "TenantType", enum_value: str) -> str:
        """
        Get the tenant type for the given enum value
        @param enum_value:
        @type enum_value:
        @return:
        @rtype:
        """
        match enum_value:
            case "Staffing":
                return "staffing"
            case "InternalHiring":
                return "internal_hiring"
            case _:
                raise ValueError(f"Unknown enum value: {enum_value}")


class EmailProvider(str, Enum):
    google = "Google"
    microsoft = "Microsoft"


class ResourceSpec(BaseResourceSpec):
    """
    ResourceSpec dataclass
    """

    limit_memory: str = "8000Mi"
    limit_cpu: str = "5000m"


class CustomerDetails(LaunchpadCLIBaseModel):
    """
    CustomerDetails dataclass
    """


class PenknifeSpec(BaseSpec):
    """
    PenknifeSpec dataclass
    """

    phoneNumber: str
    companyDomain: str
    tenantType: TenantType = TenantType.staffing
    emailProvider: EmailProvider = EmailProvider.google
    serverSpec: ResourceSpec | None = ResourceSpec()
    cliSpec: ResourceSpec | None = ResourceSpec()
