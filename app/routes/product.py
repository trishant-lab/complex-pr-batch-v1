import tempfile
import uuid
from datetime import datetime

import orjson
from fastapi import APIRouter, Depends, BackgroundTasks
from loguru import logger
from pydantic import BaseModel
from starlette.exceptions import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app import s3_utils
from app.core.db import DBManager, get_db_manager
from app.core.oauth2 import get_oauth_scheme
from app.core.settings import AppSettings, get_settings
from app.form_render import form_render_for_product
from app.models.product import ProductEnum

product_router = APIRouter()


class ProductResponseModel(BaseModel):
    id: uuid.UUID
    name: str
    product_schema: list
    created: datetime
    lastmodified: datetime
    approvalRequired: bool


@product_router.get("", operation_id="Products", response_model=list[ProductResponseModel])
async def list_all_products(
    product: None | ProductEnum = None, _: dict = Depends(get_oauth_scheme())
) -> list[ProductResponseModel]:
    """
    param product:
    param _:
    return:
    """
    config: AppSettings = get_settings()
    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        parameters = {"product_name": product.value.lower() if product else None}
        response = await db.fetch_all("listAllProducts.sql", **parameters)

        output_response = []
        for resp in response:
            resp = dict(resp)
            resp["product_schema"] = orjson.loads(resp["schema"])
            output_response.append(ProductResponseModel(**resp))

        return output_response

    except Exception as e:
        logger.error(f"Error fetching product: {e}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching product")


@product_router.get("/getProductByName", operation_id="getProductByName", response_model=ProductResponseModel)
async def get_product(product: ProductEnum, _param: dict = Depends(get_oauth_scheme())) -> ProductResponseModel:
    """
    @param product:
    @param _param:
    @return:
    """
    config: AppSettings = get_settings()
    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        response = await db.fetch_one("getProduct.sql", product=product.value.lower())

        response = dict(response)
        response["product_schema"] = orjson.loads(response["schema"])

        return ProductResponseModel(**response)

    except Exception as e:
        logger.error(f"Error fetching product: {e}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching product")


async def upload_form_to_r2_bucket(product: ProductEnum) -> None:
    """
    @param product:
    @return:
    """
    config: AppSettings = get_settings()
    form: dict = await form_render_for_product(product.value.lower())

    boto3_client = s3_utils.get_r2_storage_client(config=config)
    form_path = f"{product.value.lower()}/form.json"

    with tempfile.TemporaryDirectory() as tmp_dir:
        form_file_path = f"{tmp_dir}/form.json"
        with open(form_file_path, "w") as f:
            f.write(orjson.dumps(form).decode("utf-8"))

        s3_utils.upload_file_to_storage(
            file_path=form_file_path, object_name=form_path, bucket_name=config.r2.bucket, storage_client=boto3_client
        )


@product_router.post("/updateProductSchema", operation_id="updateProductSchema", response_model=dict)
async def update_product_schema(
    product: ProductEnum,
    product_schema: list[dict],
    background_tasks: BackgroundTasks = BackgroundTasks(),
    _param: dict = Depends(get_oauth_scheme()),
) -> dict:
    """
    @param product:
    @param product_schema:
    @param background_tasks:
    @param _param:
    @return:
    """
    config: AppSettings = get_settings()
    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        await db.execute(
            "updateProductSchema.sql",
            product_name=product.value.lower(),
            product_schema=orjson.dumps(product_schema).decode("utf-8"),
        )

        background_tasks.add_task(upload_form_to_r2_bucket, product)

        return {"message": "Updated product schema successfully"}
    except Exception as e:
        logger.error(f"Error updating product schema: {e}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error updating product schema")


@product_router.get("/renderForm", operation_id="renderForm")
async def render_form(product: ProductEnum) -> dict:
    """
    @param product:
    @param _:
    @return:
    """
    return await form_render_for_product(product.value.lower())
