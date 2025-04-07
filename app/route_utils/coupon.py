from lago_python_client.exceptions import LagoApiError

from app.core.connections import get_lago_client
from app.exceptions import errors
from app.models.lago.applied_coupon import AppliedCoupon, AppliedCouponResponse
from app.models.lago.coupon import CouponResponse
from app.models.product import ProductEnum


def get_coupon_by_code(coupon_code: str, product: ProductEnum) -> CouponResponse:
    """
    Verify the coupon code for a given email and token
    """
    lago_client = get_lago_client(product)
    try:
        coupon_resp = lago_client.coupons().find(coupon_code)
        coupon = CouponResponse.from_lago(coupon_resp)
        if coupon.terminated_at:
            raise errors.INVALID_COUPON_CODE.exc()
        return coupon
    except LagoApiError:
        raise errors.INVALID_COUPON_CODE.exc()


def apply_coupon(external_customer_id: str, coupon: CouponResponse, product: ProductEnum) -> None:
    """
    Apply coupon to customer, only one coupon is active at a time
    @param external_customer_id:
    @param coupon:
    @return:
    """
    lago_client = get_lago_client(product)
    active_coupons_resp = lago_client.applied_coupons().find_all(
        {"external_customer_id": external_customer_id, "status": "active"},
    )["applied_coupons"]

    active_coupons = [AppliedCouponResponse.from_lago(active_coupon) for active_coupon in active_coupons_resp]
    if active_coupons:
        # Destroy active coupon, apply the user provided coupon
        active_coupon = active_coupons[0]
        if active_coupon.coupon_code == coupon.code:
            return
        lago_client.applied_coupons().destroy(
            external_customer_id=external_customer_id,
            applied_coupon_id=active_coupon.lago_id,
        )
    lago_client.applied_coupons().create(
        AppliedCoupon.model_validate(
            {
                "external_customer_id": external_customer_id,
                "coupon_code": coupon.code,
            }
        ),
    )
