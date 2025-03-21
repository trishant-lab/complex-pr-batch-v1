from app.cli.temporal.core.base import LaunchpadCLIBaseModel
from app.cli.temporal.models.base_spec import BaseResourceSpec, BaseSpec


class CustomerDetails(LaunchpadCLIBaseModel):
    """
    CustomerDetails dataclass
    """


class ZSegmentSpec(BaseSpec):
    """
    ZSegmentSpec dataclass
    """

    organization: str | None = None
    emailSent: bool = False
    kestraSpec: None | BaseResourceSpec = BaseResourceSpec()
    PlanName: str = "Free"
