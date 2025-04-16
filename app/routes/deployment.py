from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Path
from loguru import logger
from pydantic_core import ValidationError

from app.core.db import DBManager, get_db_manager
from app.core.ijson import ijson_loads
from app.core.oauth2 import get_oauth_scheme
from app.exceptions import errors
from app.models.product import ProductEnum
from app.route_utils.product import validate_provisioning_details

if TYPE_CHECKING:
    from ..cli.base_workflow import ProductWorkflow


deployment_router = APIRouter()


async def deploy_workflow(tenant_name: str, product: ProductEnum) -> None:
    """
    Deploy a workflow for a tenant
    """
    try:
        db: DBManager = await get_db_manager()
        response = await db.fetch_one("get_tenant_by_name.sql", tenant_name=tenant_name, product=product.value)
        data = ijson_loads(response["data"])
        schema = ijson_loads(response["schema"])

        try:
            _, provisioning_model = await validate_provisioning_details(product=product, data=data, schema=schema)
        except ValidationError as e:
            logger.error(f"Invalid schema: {e.errors()}")
            error_message = [error["msg"] for error in e.errors()]
            raise errors.INVALID_SCHEMA.exc(e=error_message)

        deploy_schema = provisioning_model.model_dump()
        deploy_schema["customerId"] = str(response["id"])

        product_workflow: ProductWorkflow = ProductEnum.get_class(product)()
        await product_workflow.deploy(deploy_schema)

        # await product_workflow.approve(schema)
        logger.info(f"Deployed workflow for tenant: {response['tenantname']}")
    except Exception as e:
        logger.error(f"Error deploying workflow: {e}")
        raise errors.DEPLOYMENT_ERROR.exc(e=e)


@deployment_router.post("/{product}/deploy", operation_id="deployTenant", summary="Deploy tenant")
async def deploy(
    tenant_name: str,
    product: ProductEnum = Path(...),
    _: dict = Depends(get_oauth_scheme()),
) -> dict:
    """
    Deploy a workflow for a tenant
    """
    await deploy_workflow(tenant_name=tenant_name, product=product)

    return {"message": "Triggered deployment workflow"}
