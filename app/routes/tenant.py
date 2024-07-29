import uuid
from itertools import filterfalse

import orjson
from fastapi import APIRouter, Depends, Path
from loguru import logger
from starlette.exceptions import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_400_BAD_REQUEST

from app.core.db import DBManager, get_db_manager
from app.core.oauth2 import get_oauth_scheme
from app.core.settings import AppSettings, get_settings
from app.models.product import ProductEnum
from app.models.tenant import (
    TenantCreateRequestModel,
    TenantResponseModel,
)

tenant_router = APIRouter()


async def create_requestor(requestor: dict) -> dict:
    """
    @param requestor:
    @param _param:
    @return:
    """
    config: AppSettings = get_settings()
    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        response = await db.fetch_one(
            "createRequestor.sql",
            username=requestor["userName"],
            email=requestor["email"],
            organization=requestor["organization"],
        )
        return dict(response)

    except Exception as e:
        logger.error(f"Error updating requestor: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating requestor",
        )


@tenant_router.post(
    "",
    operation_id="createTenant",
)
async def create_tenant(tenant_details: TenantCreateRequestModel) -> dict:
    """
    @param tenant_details:
    @return:
    """
    config: AppSettings = get_settings()

    requestor = await create_requestor(tenant_details.requestor)
    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        return dict(
            await db.fetch_one(
                "createTenant.sql",
                **tenant_details.dict(),
                requestor_id=requestor["id"],
            )
        )

    except Exception as e:
        logger.error(f"Error creating tenant: {e}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error creating tenant")


@tenant_router.get(
    "",
    operation_id="Tenants",
    response_model=list[TenantResponseModel] | None,
)
async def list_tenants(
    product: ProductEnum, tenant_id: uuid.UUID | None = None, _param: dict = Depends(get_oauth_scheme())
) -> list[TenantResponseModel]:
    """
    @param product:
    @param tenant_id:
    @param _param:
    @return:
    """
    config: AppSettings = get_settings()
    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        parameters = {"tenant_id": str(tenant_id) if tenant_id else None, "product": product.value.lower()}
        response = await db.fetch_all("listTenants.sql", **parameters)

        output_response = []
        for tenant in response:
            tenant = dict(tenant)
            tenant["requestor"] = orjson.loads(tenant["requestor_details"])
            tenant["product_schema"] = orjson.loads(tenant["schema"]) if tenant.get("schema") else None
            tenant["product_schema"].pop("tenant") if tenant["product_schema"] and tenant.get("product_schema", {}).get(
                "tenant"
            ) else None
            tenant["provisionedDateTime"] = tenant.get("provisioneddatetime")
            output_response.append(TenantResponseModel(**tenant))

        return output_response

    except Exception as e:
        logger.error(f"Error fetching tenants: {e}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching tenants")


@tenant_router.get(
    "/getTenantById",
    operation_id="getTenantById",
    response_model=TenantResponseModel,
)
async def get_tenant(tenant_id: uuid.UUID, _param: dict = Depends(get_oauth_scheme())) -> TenantResponseModel:
    """
    @param tenant_id:
    @param _param:
    @return:
    """
    config: AppSettings = get_settings()
    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        response = await db.fetch_one("getTenantById.sql", tenant_id=str(tenant_id))

        tenant: dict = dict(response)
        tenant["requestor"] = orjson.loads(tenant["requestor_details"])
        tenant["provisionedDateTime"] = tenant.get("provisioneddatetime")

        return TenantResponseModel(**tenant)

    except Exception as e:
        logger.error(f"Error fetching tenant: {e}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching tenant")


@tenant_router.put(
    "/updateTenantDetails",
    operation_id="updateTenantDetails",
)
async def update_tenant(tenant_id: str, tenant_details: dict, _param: dict = Depends(get_oauth_scheme())) -> dict:
    """
    @param tenant_id:
    @param tenant_details:
    @param _param:
    @return:
    """
    config: AppSettings = get_settings()
    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        tenant_details = orjson.dumps(tenant_details).decode("utf-8")
        response = await db.fetch_one("updateTenantDetails.sql", schema_=tenant_details, tenant_id=tenant_id)

        return {"message": "Tenant details are updated successfully", "data": response}

    except Exception as e:
        logger.error(f"Error updating tenant: {e}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error updating tenant")


def generate_combinations(organization: str) -> list:
    """
    @param organization:
    @return:
    """
    words = organization.split()
    combinations = set()

    def helper(prefix: str, start: int) -> None:
        if len(combinations) > 20:
            return
        if start >= len(words):
            if 2 < len(prefix) < 8:
                combinations.add(prefix.lower())
        else:
            word = words[start]
            for j in range(1, len(word) + 1):
                if word[:j].isdigit():
                    continue
                new_prefix = prefix + "".join(x for x in word[:j] if x.isalpha())
                helper(new_prefix, start + 1)

    helper("", 0)
    return sorted(combinations, key=len)


async def get_valid_tenant_names(tenant_names: list) -> list:
    """
    @param tenant_names:
    @return:
    """
    config: AppSettings = get_settings()
    tenant_name_clause = ",".join([f"'{val.lower()}'" for val in tenant_names])
    if tenant_name_clause:
        params = {
            "table": "tenant",
            "columns": ["name"],
            "where": f"name in ({tenant_name_clause})",
        }
        db: DBManager = await get_db_manager(dsn=config.postgres.dsn)
        return [data["name"] for data in await db.fetch_all("get.sql", **params)]
    return []


@tenant_router.get(
    "/suggestTenantNames",
    operation_id="suggestTenantNames",
)
async def suggest_tenant_names(organization: str) -> list:
    """
    @param organization:
    @return:
    """
    combinations = generate_combinations(organization=organization)
    existing_tenants = await get_valid_tenant_names(combinations)
    existing_tenants.extend(["auth", "accounts"])
    return list(filterfalse(existing_tenants.__contains__, combinations))


@tenant_router.get(
    "/{tenant_name}",
    operation_id="validateTenantName",
)
async def verify_tenant_name(
    tenant_name: str = Path(min_length=3, max_length=15, regex="^[a-zA-Z]*$"),
) -> None:
    """
    @param tenant_name:
    @return:
    """
    tenant_names = await get_valid_tenant_names([tenant_name.lower()])
    if tenant_names:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Tenant name {tenant_name} already exists",
        )
    return
