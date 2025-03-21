import tempfile
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Path
from pydantic import BaseModel

from app import s3_utils
from app.core.db import DBManager, get_db_manager
from app.core.ijson import ijson_dumps, ijson_loads
from app.core.oauth2 import get_oauth_scheme
from app.core.settings import AppSettings, get_settings
from app.form_render import form_render_for_product
from app.models.product import ProductEnum

product_router = APIRouter()


class ProductResponseModel(BaseModel):
    name: ProductEnum
    product_schema: dict
    created: datetime
    lastmodified: datetime
    approvalRequired: bool

    @classmethod
    def json_to_model(cls, data: dict) -> "ProductResponseModel":
        """
        Convert db response to model
        """
        data["product_schema"] = ijson_loads(data["schema"])
        data["lastmodified"] = data["lastupdated"]
        return cls(**data)


@product_router.get("/listAllProducts", operation_id="listAllProducts", response_model=list[ProductResponseModel])
async def list_all_products(_: dict = Depends(get_oauth_scheme())) -> list[ProductResponseModel]:
    """
    param product:
    param _:
    return:
    """
    db: DBManager = await get_db_manager()
    response = await db.fetch_all("list_all_products.sql")

    return [ProductResponseModel.json_to_model(dict(resp)) for resp in response]


@product_router.get("/getProductByName/{product}", operation_id="getProductByName", response_model=ProductResponseModel)
async def get_product(
    product: ProductEnum = Path(...), _param: dict = Depends(get_oauth_scheme())
) -> ProductResponseModel:
    """
    @param product:
    @param _param:
    @return:
    """
    db: DBManager = await get_db_manager()
    response = await db.fetch_one("get_product.sql", product=product.value)

    return ProductResponseModel.json_to_model(dict(response))


async def upload_form_to_r2_bucket(product: ProductEnum) -> None:
    """
    @param product:
    @return:
    """
    config: AppSettings = get_settings()
    form: dict = await form_render_for_product(product.value)

    storage_client = s3_utils.get_storage_client(
        access_key=config.r2.access_key,
        secret_key=config.r2.secret_key,
        endpoint=config.r2.endpoint,
    )
    form_path = f"{product.value}/form.json"

    with tempfile.TemporaryDirectory() as tmp_dir:
        form_file_path = f"{tmp_dir}/form.json"
        with open(form_file_path, "w") as f:
            f.write(ijson_dumps(form))

        s3_utils.upload_file_to_storage(
            file_path=form_file_path, object_name=form_path, bucket_name=config.r2.bucket, storage_client=storage_client
        )


@product_router.post("/updateProductSchema/{product}", operation_id="updateProductSchema", response_model=dict)
async def update_product_schema(
    product_schema: list[dict],
    product: ProductEnum = Path(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    _: dict = Depends(get_oauth_scheme()),
) -> dict:
    """
    @param product:
    @param product_schema:
    @param background_tasks:
    @param _param:
    @return:
    """
    db: DBManager = await get_db_manager()
    await db.execute(
        "update_product_schema.sql",
        product_name=product.value,
        product_schema=ijson_dumps(product_schema),
    )

    background_tasks.add_task(upload_form_to_r2_bucket, product)

    return {"message": "Updated product schema successfully"}


@product_router.get("/renderForm/{product}", operation_id="renderForm")
async def render_form(product: ProductEnum = Path(...)) -> dict:
    """
    @param product:
    @return:
    """
    return await form_render_for_product(product.value)
