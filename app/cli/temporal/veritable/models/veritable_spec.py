from app.cli.temporal.models.base_spec import BaseResourceSpec, BaseSpec


class VeritableSpec(BaseSpec):
    """
    VeritableSpec dataclass
    """

    customerId: str
    emailSent: bool = False
    cliSpec: None | BaseResourceSpec = BaseResourceSpec()

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
