from uuid import UUID

from app.cli.temporal.core.base import LaunchpadCLIBaseModel
from app.models.product import ProductEnum


class DeboardWorkflowInput(LaunchpadCLIBaseModel):
    tenant_id: UUID
    tenant_name: str
    product: ProductEnum

    @property
    def cloudflare_r2_ui_bucket(self: "DeboardWorkflowInput") -> str:
        """
        Returns the formatted Cloudflare R2 bucket name for the current tenant and product.
        """
        domain_name = ProductEnum.get_domain(self.product)
        return f"{self.tenant_name}-{domain_name.replace('.', '-')}"

    @property
    def cloudflare_r2_data_bucket(self: "DeboardWorkflowInput") -> str:
        """
        Returns the formatted Cloudflare R2 bucket name for the current tenant and product.
        """
        return f"{self.cloudflare_r2_ui_bucket}-data"
