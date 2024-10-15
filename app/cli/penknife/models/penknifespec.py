from enum import Enum
from app.cli.temporal.core.base import LaunchpadCLIBaseModel

class TenantType(str, Enum):
    staffing = "Staffing"
    internalhiring = "InternalHiring"

    @classmethod
    def get_tenant_type(cls: "TenantType", enum_value: "TenantType") -> str:
        match enum_value:
            case cls.staffing:
                return "staffing"
            case cls.internalhiring:
                return "internal_hiring"
            case _:
                raise ValueError(f"Unknown enum value: {enum_value}")

class EmailProvider(str, Enum):
    google = "Google"
    microsoft = "Microsoft"


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

class PenknifeSpec(LaunchpadCLIBaseModel):
    """
    PenknifeSpec dataclass
    """

    tenant: str
    firstName: str
    lastName: str
    email: str
    organization: str
    contactNumber: str
    companyDomain: str
    tenantType: TenantType = TenantType.staffing
    # TODO: add emailprovider related changes to config
    emailProvider: EmailProvider = EmailProvider.google
    serverSpec: None | ResourceSpec = ResourceSpec()
    cliSpec: None | ResourceSpec = ResourceSpec()