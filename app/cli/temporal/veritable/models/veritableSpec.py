from app.cli.temporal.core.base import LaunchpadCLIBaseModel


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
    customerId: str
    firstName: str
    lastName: str
    email: str
    orgName: str
    emailSent: bool = False
    serverSpec: None | ResourceSpec = ResourceSpec()
    cliSpec: None | ResourceSpec = ResourceSpec()

    @property
    def novu_organization_name(self: "VeritableSpec") -> str:
        """
        Returns the formatted Novu organization name for the current tenant.
        """
        return f"veritable_{self.tenant}"

    @property
    def cloudflare_r2_ui_bucket(self: "VeritableSpec") -> str:
        """
        Returns the formatted Cloudflare R2 bucket name for the current tenant.
        """
        from app.models.product import ProductEnum

        domain_name = ProductEnum.get_domain(ProductEnum.veritable)
        return f"{self.tenant}-{domain_name.replace('.', '-')}"

    @property
    def cloudflare_r2_data_bucket(self: "VeritableSpec") -> str:
        """
        Returns the formatted Cloudflare R2 bucket name for the current tenant.
        """
        return f"{self.cloudflare_r2_ui_bucket}-data"
