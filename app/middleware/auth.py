import asyncio
from functools import lru_cache, wraps
from time import time
from typing import Any

import aiohttp
import jwt
import requests
from casbin.enforcer import Enforcer
from fastapi.responses import ORJSONResponse
from httpx import AsyncClient
from loguru import logger
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.settings import AppSettings, get_settings, get_security_config

config: AppSettings = get_settings()


class CredentialException(Exception):
    """Raised when there is an invalid token"""

    def __init__(self, detail: str = None):
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


@lru_cache(maxsize=1)
def get_keycloak_key() -> str:
    """
    Retrieves the certificate from keycloak jwks_uri. Parses the certificate and returns the public key from it
    """
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    from cryptography.x509 import load_pem_x509_certificate

    security_config = get_security_config()
    r: requests.Response = requests.get(security_config["jwks_uri"], timeout=60)
    rsa256_key: dict = filter(lambda x: x["alg"] == "RS256", r.json()["keys"]).__next__()
    certificate: str = f'-----BEGIN CERTIFICATE-----\n{rsa256_key["x5c"][0]}\n-----END CERTIFICATE-----'
    cert_obj = load_pem_x509_certificate(certificate.encode(), default_backend())
    return (
        cert_obj.public_key()
        .public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.PKCS1)
        .decode()
    )


def get_user(token: str) -> dict:
    """
    get user
    """
    try:
        key: str = get_keycloak_key()
        audience: list = ["account", "broker", "realm-management"]
        return jwt.decode(token, key=key, algorithms="RS256", audience=audience)
    except jwt.PyJWTError:
        raise CredentialException("Invalid token")


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
            _, token = get_token(request)
            if token:
                await self._validate_token(token)
                scope["user"] = get_user(token)
                await self.app(scope, receive, send)
            else:
                scope["user"] = {"realm_access": {"roles": ["NO_AUTH"]}}
                await self.app(scope, receive, send)
        except CredentialException:
            response = ORJSONResponse(status_code=HTTP_401_UNAUTHORIZED, content={"message": "Unauthorized"})
            await response(scope, receive, send)

    async def _validate_token(self: "AuthenticationMiddleware", token: str) -> None:
        response = await self.keycloak_client.get(
            "",
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=True,
        )
        if response.status_code == 401:
            raise CredentialException("Unauthorized")
        if response.status_code == 403:
            raise CredentialException("Forbidden")

        # async with aiohttp.ClientSession() as session:
        #     try:
        #         resp = await session.get(
        #             self.security_config["userinfo_endpoint"], headers={"Authorization": f"{scheme} {token}"}
        #         )
        #         if resp.status == 200:
        #             return await resp.json()
        #         return None
        #     except aiohttp.ClientError:
        #         return None


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
            response = ORJSONResponse(
                status_code=HTTP_403_FORBIDDEN,
                content="Forbidden"
            )

            await response(scope, receive, send)

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