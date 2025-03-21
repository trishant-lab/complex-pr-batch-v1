from fastapi import APIRouter, Depends, Path
from fastapi_limiter.depends import RateLimiter
from pydantic import EmailStr

from app.models.product import ProductEnum
from app.route_utils.recaptcha import validate_recaptcha
from app.route_utils.session_util import get_treated_email
from app.route_utils.user_otp import UserOTP

router = APIRouter()


@router.get(
    "/{product}",
    operation_id="getOTP",
    response_model=None,
    dependencies=[
        Depends(RateLimiter(seconds=30)),
        Depends(RateLimiter(times=3, seconds=300)),
    ],
)
async def get_otp(
    email: EmailStr,
    plan_name: str,
    product: ProductEnum = Path(...),
    _: str = Depends(validate_recaptcha),
) -> None:
    """
    @param email:
    @param plan_name:
    @param _:
    @return:
    """
    email = get_treated_email(email)
    await UserOTP.create_and_send_otp(email, plan_name, product)
