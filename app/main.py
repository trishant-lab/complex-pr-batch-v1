from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html, get_redoc_html
from fastapi.responses import ORJSONResponse
from loguru import logger
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse
from starlette_prometheus import PrometheusMiddleware, metrics

from .core.pycasbin.enforcer import enforcer
from .core.settings import AppSettings, get_settings
from .middleware.auth import AuthenticationMiddleware, AuthorizationMiddleware
from .routes.email_templates import email_template_router

from .routes.product import product_router
from .routes.tenant import tenant_router
from .routes.provisioning import provisioning_router
from .routes.deprovisioning import de_provisioning_router
from .routes.users import user_router

api_prefix = "/api/v1"
TITLE = "Launchpad APP"

config: AppSettings = get_settings()

ui_init_oauth: dict = {
    "realm": config.keycloak.realm,
    "clientId": config.keycloak.client_id,
}

origins: list = [
    "http://localhost:8000",
    "http://localhost:2000",
    "http://localhost:3000",
    "http://localhost:1313",
    config.keycloak.auth_url,
    "https://api-definitions.314ecorp.tech",
    "https://softwareartistry.github.io",
    "https://launchpad.314ecorp.tech",
    "https://test.314e-website.pages.dev",
    "https://314e.com",
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """
    startup and shutdown events
    """
    # All startup events go here
    logger.info("Application Startup complete!")
    yield
    # All shutdown events go here
    logger.info("Application resources cleanup and shutdown complete!")


fastapi_app = FastAPI(
    title=TITLE,
    default_response_class=ORJSONResponse,
    docs_url=None,
    redoc_url=None,
    openapi_url=f"{api_prefix}/openapi.json",
    swagger_ui_init_oauth=ui_init_oauth,
    lifespan=lifespan,
)


fastapi_app.add_middleware(PrometheusMiddleware)
fastapi_app.add_middleware(AuthorizationMiddleware, enforcer=enforcer)
fastapi_app.add_middleware(AuthenticationMiddleware)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
fastapi_app.include_router(product_router, prefix=f"{api_prefix}/product", tags=["Product"])
fastapi_app.include_router(tenant_router, prefix=f"{api_prefix}/tenant", tags=["Tenant"])
fastapi_app.include_router(provisioning_router, prefix=f"{api_prefix}/provisioning", tags=["Provisioning"])
fastapi_app.include_router(de_provisioning_router, prefix=f"{api_prefix}/deprovisioning", tags=["Deprovisioning"])
fastapi_app.include_router(user_router, prefix=f"{api_prefix}/User", tags=["User"])
fastapi_app.include_router(email_template_router, prefix=f"{api_prefix}/EmailTemplate", tags=["EmailTemplate"])
