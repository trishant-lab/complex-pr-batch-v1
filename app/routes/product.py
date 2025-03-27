from fastapi import APIRouter, Depends, Path

from app.core.db import DBManager, get_db_manager
from app.core.ijson import ijson_dumps
from app.core.oauth2 import get_oauth_scheme
from app.form_render import form_render_for_product
from app.models.product import ProductEnum
from app.route_utils.product import ProductResponseModel, upload_form_to_r2_bucket, validate_product_schema

product_router = APIRouter()


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
async def get_product(product: ProductEnum = Path(...), _: dict = Depends(get_oauth_scheme())) -> ProductResponseModel:
    """
    @param product:
    @param _:
    @return:
    """
    db: DBManager = await get_db_manager()
    response = await db.fetch_one("get_product.sql", product=product.value)

    return ProductResponseModel.json_to_model(dict(response))


@product_router.post("/updateProductSchema/{product}", operation_id="updateProductSchema", response_model=dict)
async def update_product_schema(
    product_schema: list[dict],
    product: ProductEnum = Path(...),
    _: dict = Depends(get_oauth_scheme()),
) -> dict:
    """
    @param product:
    @param product_schema:
    @return:
    """
    validate_product_schema(product, product_schema)

    db: DBManager = await get_db_manager()
    await db.execute(
        "update_product_schema.sql",
        product_name=product.value,
        product_schema=ijson_dumps(product_schema),
    )

    await upload_form_to_r2_bucket(product)
    return {"message": "Updated product schema successfully"}


@product_router.get("/renderForm/{product}", operation_id="renderForm")
async def render_form(product: ProductEnum = Path(...), _: dict = Depends(get_oauth_scheme())) -> dict:
    """
    @param product:
    @return:
    """
    return await form_render_for_product(product.value)
