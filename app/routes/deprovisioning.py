from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from loguru import logger

from app.core.db import DBManager, get_db_manager
from app.exceptions import errors

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
    product: ProductEnum = Path(...),
    tenant: UUID = Query(...),
    _: dict = Depends(get_oauth_scheme()),
) -> None:
    """
    De-provision tenant
    """
    db: DBManager = await get_db_manager()
    res = await db.fetch_one("get_tenant.sql", tenant_id=str(tenant))
    if not res:
        raise errors.TENANT_NOT_FOUND.exc()

    schema = {
        "tenant_id": tenant,
        "tenant_name": res["tenantname"],
        "product": product,
    }
    product_workflow: ProductWorkflow = ProductEnum.get_class(product)()
    await product_workflow.deboard(schema)
    logger.info(f"Triggered de-provisioning workflow for tenant: {tenant}")


@de_provisioning_router.post(
    "/{product}/approveOrDecline",
    operation_id="approveOrDeclineDeprovisioning",
)
async def approve_or_decline(
    product: ProductEnum = Path(...),
    tenant: UUID = Query(...),
    approval: bool = Query(...),
    _: dict = Depends(get_oauth_scheme()),
) -> None:
    """
    Approve or decline de-provisioning
    """
    db: DBManager = await get_db_manager()
    res = await db.fetch_one("get_tenant.sql", tenant_id=str(tenant))
    if not res:
        raise errors.TENANT_NOT_FOUND.exc()

    schema = {
        "tenant_id": tenant,
        "tenant_name": res["tenantname"],
        "product": product,
    }
    product_workflow: ProductWorkflow = ProductEnum.get_class(product)()

    if approval:
        await product_workflow.approve_deprovisioning(schema=schema)
    else:
        await product_workflow.deny_deprovisioning(schema=schema)
