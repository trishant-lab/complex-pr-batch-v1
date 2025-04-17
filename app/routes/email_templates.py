from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path
from pydantic import BaseModel, model_validator

from app.core.db import DBManager, get_db_manager
from app.core.oauth2 import get_oauth_scheme
from app.models.enums import EmailTemplateName
from app.models.product import ProductEnum

email_template_router = APIRouter()


class EmailTemplateModel(BaseModel):
    id: UUID | None = None
    name: EmailTemplateName | None = None
    subject: str
    template: str

    @model_validator(mode="before")
    @classmethod
    def validate_email_template_model(cls, data: dict) -> dict:
        """
        Validate the email template model
        """
        if not data.get("id") and not data.get("name"):
            raise ValueError("Either template id or name must be provided")
        return data


@email_template_router.get("/{product}", operation_id="getEmailTemplate")
async def get_email_template(
    product: ProductEnum = Path(...), template_id: None | UUID = None, _: dict = Depends(get_oauth_scheme())
) -> list:
    """
    Get email template
    """
    db: DBManager = await get_db_manager()
    parameters = {"product": product.value, "id": str(template_id) if template_id else None}
    response = await db.fetch_all("get_email_template.sql", **parameters)
    return [dict(row) for row in response]


@email_template_router.put("/{product}", operation_id="upsertEmailTemplate")
async def upsert_email_template(
    product: ProductEnum = Path(...),
    details: EmailTemplateModel = Body(...),
    _: dict = Depends(get_oauth_scheme()),
) -> dict:
    """
    Upsert email template templates
    """
    db: DBManager = await get_db_manager()
    params = {
        "product": product.value.lower(),
        "id": details.id,
        "name": details.name.value.lower() if details.name else None,
    }
    existing_template = await db.fetch_one("get_email_template.sql", **params)

    params = params | {"subject": details.subject, "template": details.template}
    if existing_template:
        # Update existing template
        params["id"] = existing_template["id"]
        await db.fetch_one("update_email_template.sql", **params)
    else:
        # Insert new template
        await db.fetch_one("insert_email_template.sql", **params)

    return {"message": f"Email template upserted successfully for product: {product.value}"}
