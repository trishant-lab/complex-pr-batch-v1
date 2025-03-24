from app.cli.temporal.models.base_spec import BaseResourceSpec, BaseSpec

class PricedxSpec(BaseSpec):
    """
    PricedxSpec dataclass
    """

    customerId: str | None = None
    emailSent: bool = False
    cliSpec: None | BaseResourceSpec = BaseResourceSpec()

    @property
    def cloudflare_r2_ui_bucket(self: "PricedxSpec") -> str:
        """
        Returns the formatted Cloudflare R2 bucket name for the current tenant.
        """
        from app.models.product import ProductEnum

        domain_name = ProductEnum.get_domain(ProductEnum.pricedx)
        return f"{self.tenant}-{domain_name.replace('.', '-')}"

    @property
    def cloudflare_r2_data_bucket(self: "PricedxSpec") -> str:
        """
        Returns the formatted Cloudflare R2 bucket name for the current tenant.
        """
        return f"{self.cloudflare_r2_ui_bucket}-data"
