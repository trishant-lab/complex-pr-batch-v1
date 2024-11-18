from typing import TYPE_CHECKING
from fastapi import APIRouter, Depends, HTTPException
import orjson
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from loguru import logger


from app.core.db import DBManager, get_db_manager
from app.core.oauth2 import get_oauth_scheme
from app.core.settings import AppSettings, get_settings
from app.models.product import ProductEnum

if TYPE_CHECKING:
    from ..cli.workflowbase import ProductWorkflow


deployment_router = APIRouter()


async def deploy_workflow(tenant_name: str, product: ProductEnum) -> None:
    """
    Deploy a workflow for a tenant
    """
    config: AppSettings = get_settings()

    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        response = await db.fetch_one("getTenantByName.sql", tenant_name=tenant_name, product=product.value.lower())
        schema = orjson.loads(response["schema"])
        schema["is_deployment"] = True

        product_workflow: ProductWorkflow = ProductEnum.get_class(product)()
        await product_workflow.onboard(schema)

        # await product_workflow.approve(schema)
        logger.info(f"Deployed workflow for tenant: {response['name']}")
    except Exception as e:
        logger.error(f"Error deploying workflow: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deploying workflow",
        )


@deployment_router.post("/deploy")
async def deploy(
    tenant_name: str,
    product: ProductEnum,
    _param: dict = Depends(get_oauth_scheme()),
) -> dict:
    """
    Deploy a workflow for a tenant
    """
    await deploy_workflow(tenant_name=tenant_name, product=product)

    return {"message": "Triggered deployment workflow"}
