import aiohttp
from casbin.enforcer import Enforcer
from fastapi.responses import ORJSONResponse
from httpx import AsyncClient
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.settings import AppSettings, get_security_config, get_settings

config: AppSettings = get_settings()

security_config = get_security_config()


class CredentialException(Exception):
    """Raised when there is an invalid token"""

    def __init__(self: "CredentialException", detail: None | str = None) -> None:
        self.detail = detail
        super().__init__(self.detail)


def get_token(request: Request) -> tuple[str, str]:
    """
    Retrieves token from authorization header and returns it
    :return:
    """
    authorization: str = request.headers.get("Authorization")
    scheme, token = authorization.split(" ") if authorization else (None, None)
    return scheme, token


class AuthenticationMiddleware:
    """
    Middleware for KeycloakAuth
    """

    def __init__(self: "AuthenticationMiddleware", app: ASGIApp) -> None:
        """
        Configure KeycloakAuth Middleware
        :param app:Retain for ASGI.
        """
        self.app = app
        self.security_config = get_security_config()
        self.keycloak_client = AsyncClient(base_url=self.security_config["userinfo_endpoint"], timeout=60)

    async def __call__(self: "AuthenticationMiddleware", scope: Scope, receive: Receive, send: Send) -> None:
        """
        Validate token
        """
        if scope["type"] == "lifespan":
            return await self.app(scope, receive, send)
        request = Request(scope, receive)
        try:
            latest_token = await self._validate_token(request)
            if latest_token:
                scope["user"] = latest_token
                roles = scope["user"].get("realm_access", {}).get("roles", [])
                roles.append("NO_AUTH")
                scope["user"].get("realm_access", {}).update({"roles": roles})
                await self.app(scope, receive, send)
            else:
                scope["user"] = {"realm_access": {"roles": ["NO_AUTH"]}}
                await self.app(scope, receive, send)
        except CredentialException:
            response = ORJSONResponse(status_code=HTTP_401_UNAUTHORIZED, content={"message": "Unauthorized"})
            await response(scope, receive, send)

    @staticmethod
    async def _validate_token(request: Request) -> None | dict:
        """
        Validate token
        """
        scheme, token = get_token(request)
        if not token:
            return None

        async with aiohttp.ClientSession() as session:
            try:
                resp = await session.get(
                    security_config["userinfo_endpoint"], headers={"Authorization": f"{scheme} {token}"}
                )
                if resp.status == 200:
                    return await resp.json()
                return None
            except aiohttp.ClientError:
                return None


class AuthorizationMiddleware:
    """
    Middleware for Casbin
    """

    def __init__(self: "AuthorizationMiddleware", app: ASGIApp, enforcer: Enforcer) -> None:
        """
        Configure Casbin Middleware

        :param app:Retain for ASGI.
        :param enforcer:Casbin Enforcer, must be initialized before FastAPI start.
        """
        self.app = app
        self.enforcer = enforcer

    async def __call__(self: "AuthorizationMiddleware", scope: Scope, receive: Receive, send: Send) -> None:
        """
        call
        """
        if scope["type"] == "lifespan":
            return await self.app(scope, receive, send)
        request = Request(scope, receive)
        if scope["method"] == "OPTIONS" or self._enforce(request):
            return await self.app(scope, receive, send)
        else:
            response = ORJSONResponse(status_code=HTTP_403_FORBIDDEN, content="Forbidden")

            return await response(scope, receive, send)

    def _enforce(self: "AuthorizationMiddleware", request: Request) -> bool:
        """
        Enforce a request
        """
        if "user" not in request.scope:
            return False
        user_roles: list[str] = request.scope["user"].get("realm_access", {}).get("roles", {})
        if request.url.path.endswith("/"):
            return self.enforcer.enforce(user_roles, request.url.path[:-1], request.method)
        return self.enforcer.enforce(user_roles, request.url.path, request.method)
