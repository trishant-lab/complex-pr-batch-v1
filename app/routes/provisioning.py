import orjson
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from starlette.requests import Request
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_400_BAD_REQUEST

from .product import get_product
from .tenant import create_tenant, TenantCreateRequestModel

from ..cli.workflowbase import ProductWorkflow
from ..core.db import get_db_manager, DBManager
from ..core.oauth2 import get_oauth_scheme
from ..core.settings import get_settings, AppSettings
from ..models.product import ProductEnum
from ..models.tenant import TenantStatusEnum

provisioning_router = APIRouter()


@provisioning_router.post("")
async def provisioning(
        product: ProductEnum,
        schema: dict,
        request: Request,
        skip_approval: bool = False,
        _param: dict = Depends(get_oauth_scheme())
):
    """
    Trigger provisioning workflow for the given product
    """
    user_id: dict = request.scope.get("user", {}).get("sub")
    product_details = await get_product(product=product.name, _param=_param)
    if not product_details:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Product not found")
    product_details = dict(product_details)

    # Create tenant
    await create_tenant(
        TenantCreateRequestModel(
            name=schema.get("tenant"),
            product=product_details["id"],
            status=TenantStatusEnum.PendingApproval
            if product_details["approvalRequired"] or skip_approval else TenantStatusEnum.Provisioning,
            requestor=schema.get("customerDetails"),
            approvedBy=user_id if skip_approval else None
        ),
        _param=_param
    )

    if not product_details["approvalRequired"] or skip_approval:
        # Trigger provisioning workflow
        product_workflow: ProductWorkflow = ProductEnum.get_class(product)()
        await product_workflow.onboard(schema)
        logger.info(f"Triggered provisioning workflow for product: {product}")


@provisioning_router.post("/approve")
async def approve_tenant(
        tenant_id: int,
        request: Request,
        _param: dict = Depends(get_oauth_scheme()),
):
    """
    Approve tenant
    """
    config: AppSettings = get_settings()
    user_id: dict = request.scope.get("user", {}).get("sub")
    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        response = await db.fetch_one("updateRequestor.sql", tenant_id=tenant_id)
        await db.fetch_one("approveTenant.sql", tenant_id=tenant_id, user_id=user_id)

    except Exception as e:
        logger.error(f"Error approving tenant: {e}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error approving tenant")

    schema = {
        "tenant": response["name"],
        "customerDetails": orjson.loads(response["requestor"])
    }
    product_workflow: ProductWorkflow = ProductEnum(response["product"]).value
    await product_workflow.onboard(schema)
    logger.info(f"Triggered provisioning workflow for product: {response['product']}")
