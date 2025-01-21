from fastapi import HTTPException
import aiohttp
import logging
from functools import lru_cache

from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security import OAuth2
from fastapi.security.utils import get_authorization_scheme_param
from requests import Response
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED
from .settings import get_security_config

security_config = get_security_config()

logger = logging.getLogger(__name__)


@lru_cache
async def request_client() -> aiohttp.ClientSession:
    """
    Request object with defaults
    """
    return await aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60))


def get_token(request: Request, error: bool = True) -> str | None:
    """
    Retrieves token from authorization header and returns it
    :return:
    """
    authorization: str = request.headers.get("Authorization")
    scheme, param = get_authorization_scheme_param(authorization)
    if not authorization or scheme.lower() != "bearer":
        if error:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        return None
    return param


@lru_cache
async def get_keycloak_key() -> str:
    """
    Retrieves the certificate from keycloak jwks_uri. Parses the certificate and returns the public key from it
    """
    from cryptography.x509 import load_pem_x509_certificate
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization

    r: Response = await request_client().get(security_config["jwks_uri"])
    rsa256_key: dict = filter(lambda x: x["alg"] == "RS256", r.json()["keys"]).__next__()
    certificate: str = f'-----BEGIN CERTIFICATE-----\n{rsa256_key["x5c"][0]}\n-----END CERTIFICATE-----'
    cert_obj = load_pem_x509_certificate(certificate.encode(), default_backend())
    return (
        cert_obj.public_key()
        .public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.PKCS1)
        .decode()
    )


class OAuth2ImplicitBearer(OAuth2):
    """
    Implements implicit OAuth2 flow
    """

    def __init__(
        self: "OAuth2ImplicitBearer",
        authorization_url: str,
        token_url: str,
        scheme_name: str | None = None,
        scopes: dict | None = None,
        auto_error: bool = True,
    ) -> None:
        if not scopes:
            scopes = {}
        if authorization_url:
            flows = OAuthFlowsModel(
                implicit={
                    "authorizationUrl": authorization_url,
                    "tokenUrl": token_url,
                    "scopes": scopes,
                },
            )
            super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)
        else:
            super().__init__()

    async def __call__(self: "OAuth2ImplicitBearer", request: Request) -> str | None:
        """
        returns token
        """
        return get_token(request=request, error=self.auto_error)


@lru_cache
def get_oauth_scheme() -> OAuth2ImplicitBearer:
    """
    Returns Oauth scheme with auth and token urls for a realm
    """
    return OAuth2ImplicitBearer(
        authorization_url=security_config.get("authorization_endpoint"),
        token_url=security_config.get("token_endpoint"),
        scopes={
            "email": "Email",
            "profile": "Profile data",
            "openid": "OpenID",
            "offline_access": "Offline",
        },
    )
