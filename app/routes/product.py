from fastapi import APIRouter

from app.core.db import DBManager, get_db_manager
from app.core.settings import AppSettings, get_settings

product_router = APIRouter()


@product_router.get("")
async def list_products():
    config: AppSettings = get_settings()
    db: DBManager = await get_db_manager(config.dsn)

    return await db.fetch_all("listAllProducts.sql")