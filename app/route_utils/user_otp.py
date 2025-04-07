import random
import uuid

from pydantic import EmailStr

from app.core.connections import get_redis_conn
from app.core.settings import get_settings
from app.exceptions import errors
from app.mail_templates.main import otp_verification_mail
from app.models.product import ProductEnum
from app.route_utils.session_util import _get_hashed_key
from app.sendgrid_utils import send_mail

system_random = random.SystemRandom()
settings = get_settings()


async def generate_otp(product: ProductEnum, key: EmailStr) -> int:
    """
    @param key:
    @return:
    """
    val = system_random.randint(100000, 999999)
    key = _get_hashed_key(product, key, uuid.NAMESPACE_OID) + UserOTP.SUFFIX
    redis_conn = get_redis_conn()
    await redis_conn.delete(key, key + "-c")  # delete old key and count
    await redis_conn.set(key, val, ex=UserOTP.OTP_TTL)
    return val


class UserOTP:
    """
    Use Redis as OTP store
    """

    OTP_TTL: int = 10 * 60  # 10 minutes
    MAX_RETRIES: int = 3  # Maximum 3 retry attempts allowed
    SUFFIX: str = "o"

    @staticmethod
    async def create_and_send_otp(email: EmailStr, plan_name: str, product: ProductEnum) -> None:
        """
        Creates and sends OTP to user email
        """
        otp = await generate_otp(product, email)
        app_config = ProductEnum.get_product_settings(product)
        content = otp_verification_mail(otp=otp, plan_name=plan_name, product=product)
        response = await send_mail(
            to_email=email,
            email_from=app_config.sendgrid.email_from,
            subject=f"Important: OTP Verification for {plan_name} Plan - {product.value}",
            from_name=product.value,
            content=content,
        )
        if response["responseStatus"] == 202:
            return

        key = _get_hashed_key(product, email, uuid.NAMESPACE_OID) + UserOTP.SUFFIX

        redis_conn = get_redis_conn()
        await redis_conn.delete(key, key + "-c")

        raise errors.OTP_NOT_SENT.exc()

    @staticmethod
    async def validate_otp(product: ProductEnum, email: EmailStr, otp: int) -> None:
        """
        Validates OTP for user email
        Raises error if invalid or expired
        Maximum 3 retry attempts allowed
        """
        conn = get_redis_conn()
        key = _get_hashed_key(product, email, uuid.NAMESPACE_OID) + UserOTP.SUFFIX

        async with conn.pipeline(transaction=True) as pipe:
            pipe = pipe.incr(key + "-c").mget(keys=[key, key + "-c"])
            stored_otp, retry_count = (await pipe.execute())[-1]

        if stored_otp is None:
            await conn.delete(key, key + "-c")
            raise errors.OTP_RETRY.exc()

        if str(otp) == stored_otp.decode():
            await conn.delete(key, key + "-c")
        else:
            if int(retry_count) >= UserOTP.MAX_RETRIES:
                await conn.delete(key, key + "-c")
                raise errors.OTP_RETRY.exc()
            raise errors.INVALID_OTP.exc()
