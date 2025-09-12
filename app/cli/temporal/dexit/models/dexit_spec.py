from app.cli.temporal.core.base import LaunchpadCLIBaseModel
from app.cli.temporal.models.base_spec import BaseResourceSpec, BaseSpec

OnepasswordVaultName: str = "dexit"
OnepasswordItemName: str = "dexit-tenant-config-{environment}"


class CustomerDetails(LaunchpadCLIBaseModel):
    """
    CustomerDetails dataclass
    """

    userName: str
    email: str
    organization: str


class DexitSpec(BaseSpec):
    """
    DexitSpec dataclass
    """

    organization: str | None = None
    cliSpec: BaseResourceSpec | None = BaseResourceSpec()
    planName: str = "Free"
