from fastapi import APIRouter, Depends, Path
from lago_python_client.exceptions import LagoApiError
from loguru import logger
from pydantic import EmailStr

from app.core.connections import get_lago_client
from app.core.db import DBManager, database
from app.core.oauth2 import get_oauth_scheme
from app.middleware.rate_limiter import ResilientRateLimiter
from app.models.billing_models import OnboardingResponseModel
from app.models.product import ProductEnum
from app.route_utils.lead_slack_msg import leads_otp_verified
from app.route_utils.product import validate_email_domain
from app.route_utils.session_util import get_first_subscription_status, get_treated_email
from app.route_utils.user_otp import UserOTP
from app.route_utils.user_session import UserSession

router = APIRouter()


@router.get(
    "/{product}",
    operation_id="getSession",
    dependencies=[Depends(ResilientRateLimiter(times=3, seconds=30))],
    response_model=OnboardingResponseModel,
    summary="verify and get customer details",
)
async def get_session(
    email: EmailStr,
    otp: int,
    product: ProductEnum = Path(...),
    db: DBManager = Depends(database),
) -> OnboardingResponseModel:
    """
    @param email:
    @param db:
    @return:
    """
    email = get_treated_email(email)
    validate_email_domain(product=product, email=email)
    await UserOTP.validate_otp(product, email, otp)
    token = await UserSession.get_session_token(product, email)

    provisioned, customer_record = await get_first_subscription_status(email, db, product)
    if provisioned:
        provisioned.sessionToken = token
        return provisioned

    customer = None
    if customer_record:
        try:
            lago_client = get_lago_client(product)
            customer = lago_client.customers().find(str(customer_record.pop("id"))).dict()
        except LagoApiError as e:
            logger.error(e)
        if customer:
            customer_record["tenant_name"] = customer_record.pop("tenantname")
            customer = customer | customer_record

    leads_otp_verified(email, product)
    return OnboardingResponseModel(
        sessionToken=token,
        customer=customer,
    )


@router.get(
    "/{product}/keycloak",
    operation_id="getSessionTokenByKecloak",
    dependencies=[Depends(ResilientRateLimiter(times=3, seconds=30))],
    response_model=OnboardingResponseModel,
    summary="get session token for keycloak",
)
async def get_keycloak_session(
    email: EmailStr,
    product: ProductEnum = Path(...),
    _: dict = Depends(get_oauth_scheme()),
) -> OnboardingResponseModel:
    """
    @param email:
    @param db:
    @return:
    """
    email = get_treated_email(email)
    validate_email_domain(product=product, email=email)
    token = await UserSession.get_session_token(product, email)
    return OnboardingResponseModel(
        sessionToken=token,
    )


@router.get(
    "/{product}/refresh",
    operation_id="refreshSession",
    dependencies=[Depends(ResilientRateLimiter(times=3, minutes=1))],
)
async def refresh_session(email: EmailStr, token: str, product: ProductEnum = Path(...)) -> OnboardingResponseModel:
    """
    Refreshes session token for user email
    """
    email = get_treated_email(email)
    validate_email_domain(product=product, email=email)
    new_token = await UserSession.refresh_session(product, email, token)
    return OnboardingResponseModel(
        sessionToken=new_token,
    )
