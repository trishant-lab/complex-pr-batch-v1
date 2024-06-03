from fastapi import APIRouter, Depends
from loguru import logger

from ..cli.workflowbase import ProductWorkflow
from ..core.oauth2 import get_oauth_scheme
from ..models.product import ProductEnum

de_provisioning_router = APIRouter()


@de_provisioning_router.post(
    "",
    operation_id="deprovisionTenant",
    summary="Deprovision tenant",
)
async def de_provision_tenant(product: ProductEnum, tenant: str, _: dict = Depends(get_oauth_scheme())):
    """
    Deprovision tenant
    """
    product_workflow: ProductWorkflow = product.value
    await product_workflow.onboard({"tenant": tenant})
    logger.info(f"Triggered provisioning workflow for product: {product}")
