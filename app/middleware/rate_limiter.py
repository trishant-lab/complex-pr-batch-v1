from math import ceil

import redis as pyredis
from fastapi import HTTPException
from fastapi_limiter import FastAPILimiter, default_identifier
from fastapi_limiter.depends import RateLimiter
from pydantic import EmailStr
from starlette import status
from starlette.requests import Request
from starlette.responses import Response
from websocket import WebSocket

from app.core.connections import get_redis_conn


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


class ResilientRateLimiter(RateLimiter):
    """Custom RateLimiter that attempts to reconnect to Redis on failure."""

    def __init__(self: "ResilientRateLimiter", *args, **kwargs) -> None:  # noqa: ANN003 ANN002
        """
        Initialize the Custom RateLimiter.
        """
        super().__init__(*args, **kwargs)
        self.redis_conn = None

    async def _initialize_redis(self: "ResilientRateLimiter") -> None:
        """
        Initialize the Redis connection.
        """
        if not self.redis_conn:
            self.redis_conn = get_redis_conn()
        await FastAPILimiter.init(
            self.redis_conn,
            identifier=get_rate_limiting_identifier,
            http_callback=http_callback,
        )

    async def __call__(self: "ResilientRateLimiter", request: Request, response: Response) -> None:
        """
        Custom RateLimiter that attempts to reconnect to Redis on failure.
        """
        try:
            if not FastAPILimiter.redis or not FastAPILimiter.lua_sha:
                await self._initialize_redis()

            return await super().__call__(request, response)
        except pyredis.exceptions.ResponseError:
            await self._initialize_redis()
            return await super().__call__(request, response)
