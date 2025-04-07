from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Path
from loguru import logger
from pydantic.fields import PydanticUndefined

from ..core.oauth2 import get_oauth_scheme
from ..models.product import ProductEnum

de_provisioning_router = APIRouter()


if TYPE_CHECKING:
    from ..cli.base_workflow import ProductWorkflow


@de_provisioning_router.post(
    "/{product}",
    operation_id="deprovisionTenant",
    summary="Deprovision tenant",
)
async def de_provision_tenant(
    tenant: str,
    product: ProductEnum = Path(...),
    _: dict = Depends(get_oauth_scheme()),
) -> None:
    """
    De-provision tenant
    """
    product_workflow: ProductWorkflow = ProductEnum.get_class(product)()
    schema = {}
    for key, value in ProductEnum.get_input_model_class(product).model_fields.items():
        if value.default is not None and value.default != PydanticUndefined:
            schema[key] = value.default
        else:
            schema[key] = ""
    schema["tenant"] = tenant
    await product_workflow.deboard(schema)
    await product_workflow.approve_deprovisioning(schema=schema)
    logger.info(f"Triggered de-provisioning workflow for tenant: {tenant}")
