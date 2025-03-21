from fastapi import APIRouter, Depends, Path
from fastapi_limiter.depends import RateLimiter
from lago_python_client.exceptions import LagoApiError
from loguru import logger
from pydantic import EmailStr

from app.core.connections import get_lago_client
from app.core.db import DBManager, database
from app.models.billing_models import OnboardingResponseModel
from app.models.product import ProductEnum
from app.route_utils.lead_slack_msg import leads_otp_verified
from app.route_utils.session_util import get_first_subscription_status, get_treated_email
from app.route_utils.user_otp import UserOTP
from app.route_utils.user_session import UserSession

router = APIRouter()


@router.get(
    "/{product}",
    operation_id="getSession",
    dependencies=[Depends(RateLimiter(times=3, seconds=30))],
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
    await UserOTP.validate_otp(product, email, otp)
    token = await UserSession.create_session(product, email)

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
    "/{product}/refresh",
    operation_id="refreshSession",
    dependencies=[Depends(RateLimiter(times=3, minutes=1))],
)
async def refresh_session(email: EmailStr, token: str, product: ProductEnum = Path(...)) -> OnboardingResponseModel:
    """
    Refreshes session token for user email
    """
    email = get_treated_email(email)
    new_token = await UserSession.refresh_session(product, email, token)
    return OnboardingResponseModel(
        sessionToken=new_token,
    )
