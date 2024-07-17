from uuid import UUID

from fastapi import APIRouter, Path, Depends
from loguru import logger
from starlette.exceptions import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app.core.db import DBManager, get_db_manager
from app.core.oauth2 import get_oauth_scheme
from app.core.settings import AppSettings, get_settings
from app.models.product import ProductEnum

email_template_router = APIRouter()


@email_template_router.get("/{product}", operation_id="getEmailTemplate")
async def get_email_template(
    product: ProductEnum = Path(...), template_id: None | UUID = None, _param: dict = Depends(get_oauth_scheme())
) -> list:
    """
    Get email template
    """
    config: AppSettings = get_settings()
    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        parameters = {"product": product.value, "template_id": str(template_id) if template_id else None}
        response = await db.fetch_all("getEmailTemplate.sql", **parameters)
    except Exception as e:
        logger.error(f"Error fetching template: {e}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching email template")

    return [dict(row) for row in response]


@email_template_router.put("/{product}", operation_id="updateEmailTemplate")
async def update_email_template(
    template: str, template_id: UUID, product: ProductEnum = Path(...), _param: dict = Depends(get_oauth_scheme())
) -> dict:
    """
    Update email template
    """
    config: AppSettings = get_settings()
    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        parameters = {
            "product": product.value,
            "template_id": str(template_id) if template_id else None,
            "template": template,
        }
        await db.fetch_one("updateEmailTemplate.sql", **parameters)
    except Exception as e:
        logger.error(f"Error updating template: {e}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error updating email template")

    return {"message": f"Email template updated successfully for product: {product}"}
