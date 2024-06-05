import orjson
from fastapi import APIRouter, Depends
from loguru import logger
from starlette.exceptions import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app.core.db import DBManager, get_db_manager
from app.core.oauth2 import get_oauth_scheme
from app.core.settings import AppSettings, get_settings
from app.models.product import ProductEnum
from app.models.tenant import TenantCreateRequestModel, TenantResponseModel, UpdateRequestorModel

tenant_router = APIRouter()


async def create_requestor(requestor: dict, _param: dict = Depends(get_oauth_scheme())):
    config: AppSettings = get_settings()
    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        response = await db.fetch_one(
            "createRequestor.sql",
            username=requestor['userName'],
            email=requestor['email'],
            organization=requestor['organization'],
        )
        return response

    except Exception as e:
        logger.error(f"Error updating requestor: {e}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error updating requestor")


@tenant_router.post(
    "",
    operation_id="createTenant",
)
async def create_tenant(tenant_details: TenantCreateRequestModel, _param: dict = Depends(get_oauth_scheme())):
    config: AppSettings = get_settings()

    requestor = await create_requestor(tenant_details.requestor, _param=_param)
    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        response = await db.fetch_one("createTenant.sql", **tenant_details.dict(), requestor_id=requestor['id'])

        return response

    except Exception as e:
        logger.error(f"Error creating tenant: {e}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error creating tenant")


@tenant_router.get(
    "/listAllTenantsPerProduct",
    operation_id="listAllTenantsPerProduct",
    response_model=list[TenantResponseModel] | None,
)
async def list_tenants(product: ProductEnum, _param: dict = Depends(get_oauth_scheme())):
    config: AppSettings = get_settings()
    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        response = await db.fetch_all("listTenants.sql", product=product.name)

        output_response = []
        for tenant in response:
            tenant = dict(tenant)
            tenant['requestor'] = orjson.loads(tenant['requestor_details'])
            output_response.append(TenantResponseModel(**tenant))

        return output_response

    except Exception as e:
        logger.error(f"Error fetching tenants: {e}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching tenants")


@tenant_router.put(
    "/updateRequestorDetails",
    operation_id="updateRequestorDetails",
)
async def update_tenant(requestor_details: UpdateRequestorModel, _param: dict = Depends(get_oauth_scheme())):
    config: AppSettings = get_settings()
    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        response = await db.fetch_one("updateRequestor.sql", **requestor_details.dict())

        return {
            "message": "Requestor details updated successfully",
            "data": response
        }

    except Exception as e:
        logger.error(f"Error updating tenant: {e}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error updating tenant")
