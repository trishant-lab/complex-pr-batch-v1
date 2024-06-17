from datetime import datetime
import uuid

import orjson
from fastapi import APIRouter, Depends
from loguru import logger
from pydantic import BaseModel
from starlette.exceptions import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app.core.db import DBManager, get_db_manager
from app.core.oauth2 import get_oauth_scheme
from app.core.settings import AppSettings, get_settings

product_router = APIRouter()


class ProductResponseModel(BaseModel):
    id: uuid.UUID
    name: str
    product_schema: dict
    created: datetime
    lastmodified: datetime
    approvalRequired: bool


@product_router.get("/listAllProducts", operation_id="listAllProducts", response_model=list[ProductResponseModel])
async def list_all_products(_: dict = Depends(get_oauth_scheme())) -> list[ProductResponseModel]:
    """
    @param _:
    @return:
    """
    config: AppSettings = get_settings()
    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        response = await db.fetch_all("listAllProducts.sql")

        output_response = []
        for resp in response:
            resp = dict(resp)
            resp["product_schema"] = orjson.loads(resp["schema"])
            output_response.append(ProductResponseModel(**resp))

        return output_response

    except Exception as e:
        logger.error(f"Error fetching product: {e}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching product")


@product_router.get("/getProduct", operation_id="getProduct", response_model=ProductResponseModel)
async def get_product(product: str, _param: dict = Depends(get_oauth_scheme())) -> ProductResponseModel:
    """
    @param product:
    @param _param:
    @return:
    """
    config: AppSettings = get_settings()
    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        response = await db.fetch_one("getProduct.sql", product=product)

        response = dict(response)
        response["product_schema"] = orjson.loads(response["schema"])

        return ProductResponseModel(**response)

    except Exception as e:
        logger.error(f"Error fetching product: {e}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching product")
