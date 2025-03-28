from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends
from loguru import logger

from app.core.db import DBManager, get_db_manager
from app.core.ijson import ijson_loads
from app.core.oauth2 import get_oauth_scheme
from app.exceptions import errors
from app.models.product import ProductEnum

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
        schema = ijson_loads(response["schema"])
        schema["is_deployment"] = True

        product_workflow: ProductWorkflow = ProductEnum.get_class(product)()
        await product_workflow.onboard(schema)

        # await product_workflow.approve(schema)
        logger.info(f"Deployed workflow for tenant: {response['name']}")
    except Exception as e:
        logger.error(f"Error deploying workflow: {e}")
        raise errors.DEPLOYMENT_ERROR.exc(e=e)


@deployment_router.post("/deploy")
async def deploy(
    tenant_name: str,
    product: ProductEnum,
    _: dict = Depends(get_oauth_scheme()),
) -> dict:
    """
    Deploy a workflow for a tenant
    """
    await deploy_workflow(tenant_name=tenant_name, product=product)

    return {"message": "Triggered deployment workflow"}
