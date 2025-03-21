from fastapi import APIRouter, Depends, Path
from fastapi_limiter.depends import RateLimiter
from pydantic import EmailStr

from app.core.db import DBManager, get_db_manager
from app.exceptions import errors
from app.mail_templates.main import tenant_link_mail
from app.models.product import ProductEnum
from app.route_utils.recaptcha import validate_recaptcha
from app.route_utils.session_util import get_treated_email
from app.sendgrid_utils import send_mail

router = APIRouter()


@router.post(
    "/{product}",
    operation_id="getPortalLink",
    dependencies=[
        Depends(RateLimiter(seconds=10)),
        Depends(RateLimiter(times=5, seconds=60)),
    ],
)
async def get_portal_link(
    email: EmailStr,
    product: ProductEnum = Path(...),
    _: str = Depends(validate_recaptcha),
) -> None:
    """
    @param email:
    @param _:
    @return:
    """
    email = get_treated_email(email)
    app_config = ProductEnum.get_product_settings(product)

    if email != app_config.sendgrid.support_mail:
        db: DBManager = await get_db_manager()
        env_prefix = "https://"
        tenant_links = await db.fetch_all(
            "get_tenant_link.sql",
            email=email,
            env_suffix=f".{app_config.tenant_fqdn}",
            env_prefix=env_prefix,
            product=product.value,
        )
        if not tenant_links:
            raise errors.CUSTOMER_NOT_FOUND.exc()
        suffix = "s" if len(tenant_links) > 1 else ""
        subject = f"Important: Link{suffix} to your {product.value} Portal{suffix}"
        content = tenant_link_mail(tenant_links=tenant_links, product=product)
        response = await send_mail(
            to_email=email,
            subject=subject,
            from_name=product.value,
            email_from=app_config.sendgrid_email_from,
            content=content,
        )
        if response["responseStatus"] != 202:
            raise errors.TENANT_LINK_NOT_SENT.exc()
