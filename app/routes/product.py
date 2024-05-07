from datetime import datetime
import uuid
from typing import List

import orjson
from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel
from starlette.exceptions import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app.core.db import DBManager, get_db_manager
from app.core.settings import AppSettings, get_settings

product_router = APIRouter()


class ProductResponseModel(BaseModel):
    id: uuid.UUID
    name: str
    product_schema: dict
    created: datetime
    lastmodified: datetime


@product_router.get(
    "/listAllProducts",
    operation_id="listAllProducts",
    response_model=List[ProductResponseModel]
)
async def list_all_products():
    config: AppSettings = get_settings()
    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        response = await db.fetch_all("listAllProducts.sql")

        output_response = []
        for resp in response:
            resp = dict(resp)
            resp["product_schema"] = orjson.loads(resp["schema"])
            output_response.append(resp)

        return output_response

    except Exception as e:
        logger.error(f"Error fetching product: {e}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching product")


@product_router.get(
    "/getProduct",
    operation_id="getProduct",
    response_model=ProductResponseModel
)
async def get_product(product_id: uuid.UUID):
    config: AppSettings = get_settings()
    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        response = await db.fetch_one("getProduct.sql", product_id=product_id)

        response = dict(response)
        response["product_schema"] = orjson.loads(response["schema"])

        return response

    except Exception as e:
        logger.error(f"Error fetching product: {e}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching product")
