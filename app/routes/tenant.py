import uuid
from typing import TYPE_CHECKING

from better_profanity import profanity
from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query
from loguru import logger
from pydantic import EmailStr
from temporalio.client import WorkflowHandle

from app.core.db import DBManager, get_db_manager
from app.core.ijson import ijson_dumps
from app.core.oauth2 import get_oauth_scheme
from app.exceptions import errors
from app.models.input_param_patterns import TENANT_NAME_PATTERN
from app.models.product import ProductEnum
from app.models.tenant import (
    SuggestTenantNamesResponseModel,
    TenantCreateRequestModel,
    TenantResponseModel,
    TenantStatusEnum,
)
from app.route_utils.product import validate_email_domain
from app.route_utils.tenant_suggestions import get_existing_tenant_names, get_valid_suggestions

if TYPE_CHECKING:
    from app.cli.base_workflow import ProductWorkflow

tenant_router = APIRouter()


async def create_tenant(tenant_details: TenantCreateRequestModel) -> dict:
    """
    @param tenant_details:
    @return:
    """
    db: DBManager = await get_db_manager()
    return dict(
        await db.fetch_one(
            "create_tenant.sql",
            errors=ijson_dumps({"error": "NA"}),
            **tenant_details.model_dump(),
        )
    )


@tenant_router.get(
    "/{product}",
    operation_id="Tenants",
    response_model=list[TenantResponseModel] | None,
)
async def list_tenants(
    product: ProductEnum = Path(...), tenant_id: uuid.UUID | None = None, _: dict = Depends(get_oauth_scheme())
) -> list[TenantResponseModel]:
    """
    @param product:
    @param tenant_id:
    @param _:
    @return:
    """
    db: DBManager = await get_db_manager()
    parameters = {"tenant_id": str(tenant_id) if tenant_id else None, "product": product.value}
    response = await db.fetch_all("list_tenants.sql", **parameters)
    return [TenantResponseModel.json_to_model(dict(tenant)) for tenant in response]


async def update_provisioning_workflow(product: ProductEnum, tenant_details: dict) -> None:
    """
    @param product:
    @param tenant_details:
    @return:
    """
    tenant_details["tenant"] = (
        tenant_details.get("tenantName") if tenant_details.get("tenantName") else tenant_details.get("tenant")
    )
    product_workflow: ProductWorkflow = ProductEnum.get_class(product)()

    workflow_handle: WorkflowHandle = await product_workflow.get_workflow_handle(schema=tenant_details)

    response = await workflow_handle.describe()

    if response.status.name == "RUNNING":
        # terminate the workflow
        await workflow_handle.terminate()

    # start the workflow
    await product_workflow.onboard(tenant_details)

    logger.info(f"Triggered provisioning workflow for product: {product.value}")


@tenant_router.put(
    "/updateTenantDetails/{product}",
    operation_id="updateTenantDetails",
)
async def update_tenant(
    tenant_id: str,
    tenant_details: dict,
    product: ProductEnum = Path(..., alias="product"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    _: dict = Depends(get_oauth_scheme()),
) -> dict:
    """
    @param product:
    @param tenant_id:
    @param tenant_details:
    @param background_tasks:
    @param _:
    @return:
    """
    db: DBManager = await get_db_manager()
    tenant = await db.fetch_one("get_tenant.sql", tenant_id=tenant_id)
    if not tenant:
        raise errors.TENANT_NOT_FOUND.exc()

    if not TenantStatusEnum.can_update_tenant(TenantStatusEnum(tenant["status"])):
        raise errors.TENANT_DETAILS_CANNOT_BE_UPDATED.exc()

    tenant_details_str = ijson_dumps(tenant_details)
    response = await db.fetch_one("update_tenant_details.sql", schema_=tenant_details_str, tenant_id=tenant_id)

    background_tasks.add_task(update_provisioning_workflow, product, tenant_details)

    return {"message": "Tenant details are updated successfully", "data": response}


@tenant_router.get(
    "/suggestTenantNames/{product}",
    operation_id="suggestTenantNames",
)
async def suggest_tenant_names(
    product: ProductEnum = Path(...),
    email: EmailStr = Query(...),
    organization: str = Query(...),
    _: dict = Depends(get_oauth_scheme()),
) -> SuggestTenantNamesResponseModel:
    """
    @param organization:
    @param product:
    @return:
    """
    validate_email_domain(product=product, email=email)
    tenant_names = await get_valid_suggestions(product=product, email=email, organization=organization)
    return SuggestTenantNamesResponseModel(
        tenant_names=tenant_names,
        domain=ProductEnum.get_domain(product),
    )


@tenant_router.get(
    "/{product}/validateTenantName/{tenant_name}",
    operation_id="validateTenantName",
)
async def verify_tenant_name(
    tenant_name: str = Path(pattern=TENANT_NAME_PATTERN),
    product: ProductEnum = Path(...),
    email: EmailStr = Query(...),
    _: dict = Depends(get_oauth_scheme()),
) -> None:
    """
    @param product:
    @param tenant_name:
    @return:
    """
    validate_email_domain(product=product, email=email)
    tenant_names = await get_existing_tenant_names(product=product, email=email, tenant_names=[tenant_name.lower()])
    if tenant_names:
        raise errors.ALREADY_ALLOCATED_TENANT_NAME.exc()
    if profanity.contains_profanity(tenant_name):
        raise errors.EXPLICIT_WORDS_NOT_ALLOWED.exc()
