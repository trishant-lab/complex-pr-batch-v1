from fastapi import APIRouter, Depends, Path
from pydantic import EmailStr

from app.core.db import DBManager, get_db_manager
from app.exceptions import errors
from app.middleware.rate_limiter import ResilientRateLimiter
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum
from app.route_utils.product import validate_email_domain
from app.route_utils.recaptcha import validate_recaptcha
from app.route_utils.session_util import get_treated_email
from app.route_utils.user_otp import UserOTP

router = APIRouter()


@router.get(
    "/{product}/OTP",
    operation_id="getOTPForPortalLink",
    dependencies=[
        Depends(ResilientRateLimiter(seconds=10)),
        Depends(ResilientRateLimiter(times=5, seconds=60)),
    ],
)
async def get_otp_for_portal_link(
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
    validate_email_domain(product=product, email=email)
    await UserOTP.create_portal_link_otp(email, product)


@router.post(
    "/{product}",
    operation_id="getPortalLink",
    dependencies=[Depends(ResilientRateLimiter(times=3, seconds=30))],
)
async def get_portal_link(
    email: EmailStr,
    otp: int,
    product: ProductEnum = Path(...),
) -> list[str]:
    """
    @param email:
    @param _:
    @return:
    """
    await UserOTP.validate_otp(product, email, otp, UserOTP.PORTAL_LINK_OTP_SUFFIX)
    app_config = ProductEnum.get_product_settings(product)

    email = get_treated_email(email)
    if email != app_config.sendgrid.support_mail:
        db: DBManager = await get_db_manager()
        env_prefix = "https://"
        tenant_links = await db.fetch_all(
            "get_tenant_link_from_keycloak.sql",
            email=email,
            env_suffix=app_config.tenant_fqdn,
            env_prefix=env_prefix,
            product=product.value.lower(),
            roles=ProductEnum.get_client_roles(product),
            TenantStatusEnum=TenantStatusEnum,
        )
        urls = [x["tenantlinks"] for x in tenant_links]
        if tenant_links:
            return urls
        raise errors.CUSTOMER_NOT_FOUND.exc()
    raise errors.TENANT_LINK_NOT_SENT.exc()
