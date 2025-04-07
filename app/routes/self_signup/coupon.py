from fastapi import APIRouter, Path, Query
from pydantic import EmailStr

from app.models.input_param_patterns import TOKEN_PATTERN
from app.models.lago.coupon import CouponResponse
from app.models.product import ProductEnum
from app.route_utils.coupon import get_coupon_by_code
from app.route_utils.user_session import UserSession

router = APIRouter()


@router.get("/{product}", operation_id="verifyCoupon")
async def verify_coupon(
    email: EmailStr,
    product: ProductEnum = Path(...),
    token: str = Query(..., regex=TOKEN_PATTERN),
    coupon_code: str = Query(..., min_length=3, max_length=15),
) -> CouponResponse:
    """
    Verify the coupon code for a given email and token
    """
    await UserSession.validate_session(product=product, email=email, session_token=token)
    return get_coupon_by_code(coupon_code=coupon_code, product=product)
