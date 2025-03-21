from uuid import UUID

from fastapi import APIRouter, Depends, Path

from app.core.db import DBManager, get_db_manager
from app.core.oauth2 import get_oauth_scheme
from app.models.product import ProductEnum

email_template_router = APIRouter()


@email_template_router.get("/{product}", operation_id="getEmailTemplate")
async def get_email_template(
    product: ProductEnum = Path(...), template_id: None | UUID = None, _param: dict = Depends(get_oauth_scheme())
) -> list:
    """
    Get email template
    """
    db: DBManager = await get_db_manager()
    parameters = {"product": product.value, "template_id": str(template_id) if template_id else None}
    response = await db.fetch_all("get_email_template.sql", **parameters)
    return [dict(row) for row in response]


@email_template_router.put("/{product}", operation_id="updateEmailTemplate")
async def update_email_template(
    template: str,
    subject: str,
    template_id: UUID,
    product: ProductEnum = Path(...),
    _param: dict = Depends(get_oauth_scheme()),
) -> dict:
    """
    Update email template
    """
    db: DBManager = await get_db_manager()
    parameters = {
        "product": product.value,
        "template_id": str(template_id),
        "template": template,
        "subject": subject,
    }
    await db.fetch_one("update_email_template.sql", **parameters)
    return {"message": f"Email template updated successfully for product: {product.value}"}
