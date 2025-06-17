from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from asyncpg import PostgresError
from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.responses import ORJSONResponse
from loguru import logger
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse
from starlette_prometheus import PrometheusMiddleware, metrics

from app.exceptions.error_code_mapper import LaunchpadHTTPException
from app.middleware.exception_handler import (
    generic_exception_handler,
    launchpad_http_exception_handler,
    postgres_exception_handler,
)
from app.middleware.log_metrics import LoggerMiddleware

from .core.pycasbin.enforcer import enforcer
from .core.settings import AppSettings, get_settings
from .middleware.auth import AuthenticationMiddleware, AuthorizationMiddleware
from .routes.deployment import deployment_router
from .routes.deprovisioning import de_provisioning_router
from .routes.email_templates import email_template_router
from .routes.product import product_router
from .routes.provisioning import provisioning_router
from .routes.self_signup.add_ons import router as add_ons_router
from .routes.self_signup.coupon import router as coupon_router
from .routes.self_signup.onboard import router as onboard_router
from .routes.self_signup.plans import router as plans_router
from .routes.self_signup.signup import router as signup_router
from .routes.self_signup.subscriptions import router as subscriptions_router
from .routes.self_signup.tenant_link import router as tenant_link_router
from .routes.self_signup.user_otp import router as user_otp_router
from .routes.self_signup.user_session import router as user_session_router
from .routes.tenant import tenant_router
from .routes.users import user_router
from .routes.webhooks import router as webhook_router

API_PREFIX = "/api/v1"
TITLE = "Launchpad APP"

config: AppSettings = get_settings()

ui_init_oauth: dict = {
    "realm": config.keycloak.realm,
    "clientId": config.keycloak.client_id,
}

DOMAINS = [
    r"veritable\.app",
    r"veritable\.work",
    r"314ecorp\.tech",
    r"314ecorp\.com",
    r"314e\.com",
    r"314e\.tech",
    r"314e\.app",
    r"pricedx\.tech",
    r"pricedx\.com",
    r"api\.314e\.app",
    r"api\.314e\.com",
]

origins: list = [
    "http://localhost:8000",
    "http://localhost:2000",
    "http://localhost:3000",
    "http://localhost:1313",
    "https://softwareartistry.github.io",
    "https://veritable-app.pages.dev",
    "https://test.veritable-app.pages.dev",
    "https://test2.veritable-app.pages.dev",
    "https://test.314e-website.pages.dev",
]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """
    startup and shutdown events
    """
    # All startup events go here
    from app.models.product import validate_self_signup_products
    from app.route_utils.addons_util import prefetch_addons
    from app.route_utils.plans_util import prefetch_plans

    validate_self_signup_products()
    await prefetch_addons()
    await prefetch_plans()
    yield
    # All shutdown events go here
    logger.info("Application resources cleanup and shutdown complete!")


fastapi_app = FastAPI(
    title=TITLE,
    default_response_class=ORJSONResponse,
    docs_url=None,
    redoc_url=None,
    openapi_url=f"{API_PREFIX}/openapi.json",
    swagger_ui_init_oauth=ui_init_oauth,
    lifespan=lifespan,
)


# Add all middlewares. The order of middleware is very important
fastapi_app.exception_handler(Exception)(generic_exception_handler)
fastapi_app.exception_handler(PostgresError)(postgres_exception_handler)
fastapi_app.exception_handler(LaunchpadHTTPException)(launchpad_http_exception_handler)
fastapi_app.add_middleware(PrometheusMiddleware)
fastapi_app.add_middleware(AuthorizationMiddleware, enforcer=enforcer)
fastapi_app.add_middleware(AuthenticationMiddleware)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=rf"^https?:\/\/([a-z0-9-]+\.)({'|'.join(DOMAINS)})$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fastapi_app.add_middleware(LoggerMiddleware)

fastapi_app.add_route("/metrics", metrics)


@fastapi_app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse:
    """Returns custom swagger UI"""
    return get_swagger_ui_html(
        openapi_url=fastapi_app.openapi_url,
        title=TITLE + " - Swagger UI",
        oauth2_redirect_url=fastapi_app.swagger_ui_oauth2_redirect_url,
        swagger_favicon_url="https://314e.com/wp-content/uploads/2019/10/cropped-314e_logo_2016-300x300-150x150.png",
    )


@fastapi_app.get(fastapi_app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect() -> HTMLResponse:
    """Returns Swagger UI oauth2 redirect HTMLComponent"""
    return get_swagger_ui_oauth2_redirect_html()


@fastapi_app.get("/redoc", include_in_schema=False)
async def redoc_html() -> HTMLResponse:
    """Return Redoc HTML"""
    return get_redoc_html(
        openapi_url=fastapi_app.openapi_url,
        title=TITLE + " - ReDoc",
        redoc_favicon_url="https://314e.com/wp-content/uploads/2019/10/cropped-314e_logo_2016-300x300-150x150.png",
        with_google_fonts=False,
    )


# Adding application routes to FastAPI instance
fastapi_app.include_router(plans_router, prefix=f"{API_PREFIX}/plans", tags=["Plans"])
fastapi_app.include_router(add_ons_router, prefix=f"{API_PREFIX}/addOns", tags=["AddOns"])
fastapi_app.include_router(coupon_router, prefix=f"{API_PREFIX}/coupon", tags=["Coupon"])
fastapi_app.include_router(tenant_link_router, prefix=f"{API_PREFIX}/portalLink", tags=["Portal"])
fastapi_app.include_router(user_otp_router, prefix=f"{API_PREFIX}/otp", tags=["OTP"])
fastapi_app.include_router(user_session_router, prefix=f"{API_PREFIX}/session", tags=["User Session"])
fastapi_app.include_router(signup_router, prefix=f"{API_PREFIX}/signup", tags=["Signup"])
fastapi_app.include_router(subscriptions_router, prefix=f"{API_PREFIX}/subscriptions", tags=["Subscriptions"])
fastapi_app.include_router(onboard_router, prefix=f"{API_PREFIX}/onboard", tags=["Onboard"])
fastapi_app.include_router(product_router, prefix=f"{API_PREFIX}/product", tags=["Product"])
fastapi_app.include_router(tenant_router, prefix=f"{API_PREFIX}/tenant", tags=["Tenant"])
fastapi_app.include_router(provisioning_router, prefix=f"{API_PREFIX}/provisioning", tags=["Provisioning"])
fastapi_app.include_router(de_provisioning_router, prefix=f"{API_PREFIX}/deprovisioning", tags=["Deprovisioning"])
fastapi_app.include_router(user_router, prefix=f"{API_PREFIX}/User", tags=["User"])
fastapi_app.include_router(email_template_router, prefix=f"{API_PREFIX}/EmailTemplate", tags=["EmailTemplate"])
fastapi_app.include_router(deployment_router, prefix=f"{API_PREFIX}/deployment", tags=["Deployment"])
fastapi_app.include_router(webhook_router, prefix=f"{API_PREFIX}/webhooks", tags=["Webhooks"])
