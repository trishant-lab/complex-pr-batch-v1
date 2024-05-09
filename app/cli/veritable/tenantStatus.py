from loguru import logger
from starlette.exceptions import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app.core.db import DBManager, get_db_manager
from app.core.settings import AppSettings, get_settings
from app.cli.veritable.common import ProductName


async def update_tenant_status(tenant_name: str, status: str, error_message: None | str = None):
    config: AppSettings = get_settings()
    try:
        parameters = {
            "tenant_name": tenant_name,
            "product": ProductName,
            "status": status,
            "error_message": error_message
        }
        db: DBManager = await get_db_manager(config.postgres.dsn)
        await db.fetch_one(
            "updateTenant.sql",
            db_schema_name=config.postgres.schema_name,
            **parameters
        )

    except Exception as e:
        logger.error(f"Error while updating tenant status for {tenant_name}: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while updating tenant status {tenant_name}"
        )
