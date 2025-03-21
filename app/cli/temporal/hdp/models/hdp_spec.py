from app.cli.temporal.models.base_spec import BaseResourceSpec, BaseSpec


class HDPSpec(BaseSpec):
    """
    HDPSPec dataclass
    """

    emailSent: bool = False
    organization: str | None = None
    kestraSpec: None | BaseResourceSpec = BaseResourceSpec()
