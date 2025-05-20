import httpx

from app.core.settings import get_settings
from app.exceptions import errors

APPLICATION_CONFIG = get_settings()


def validate_recaptcha(captcha: str) -> None:
    """
    @param captcha:
    @return:
    """
    cf_recaptcha_resp = httpx.post(
        url=APPLICATION_CONFIG.recaptcha.api_url,
        data={"secret": APPLICATION_CONFIG.recaptcha.secret_key, "response": captcha},
        timeout=60,
    ).json()
    if not cf_recaptcha_resp["success"]:
        raise errors.RECAPTCHA_FAILED.exc()
