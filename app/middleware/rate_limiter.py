from math import ceil

from fastapi import HTTPException
from fastapi_limiter import default_identifier
from pydantic import EmailStr
from starlette import status
from starlette.requests import Request
from starlette.responses import Response
from websocket import WebSocket


async def get_rate_limiting_identifier(request: Request | WebSocket) -> str | EmailStr:
    """
    @param request:
    @return:
    """
    if request.url.path.startswith("/otp") or request.url.path.startswith("/subscriptions"):
        from ..route_utils.session_util import get_treated_email

        return get_treated_email(EmailStr(request.query_params["email"]))
    return await default_identifier(request)


async def http_callback(_request: Request, _response: Response, pexpire: int) -> None:
    """
    callback when too many requests
    :return:
    """
    detail = {
        "code": "",
        "displayMessage": "Too Many Requests",
        "followUpAction": [],
        "possibleResolutions": ["Please retry in some time."],
    }
    expire = ceil(pexpire / 1000)
    raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail, headers={"Retry-After": str(expire)})
