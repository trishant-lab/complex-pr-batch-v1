from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html, get_redoc_html
from fastapi.responses import ORJSONResponse
from loguru import logger
from starlette.responses import HTMLResponse

from .core.settings import AppSettings, get_settings

from .routes.product import product_router
from .routes.onboarding import onboarding_router
from .routes.deprovisioning import deprovisioning_router

api_prefix = "/api/v1"
TITLE = f"Onboarding APP"

config: AppSettings = get_settings()

ui_init_oauth: dict = {
    "realm": config.keycloak.realm,
    "clientId": config.keycloak.client_id,
}


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
fastapi_app.include_router(onboarding_router, prefix=f"{api_prefix}/onboarding", tags=["Onboarding"])
fastapi_app.include_router(deprovisioning_router, prefix=f"{api_prefix}/deprovisioning", tags=["Deprovisioning"])
