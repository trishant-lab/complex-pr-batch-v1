from urllib.parse import urlparse

import jwt
from fastapi import APIRouter, HTTPException, Path, Request
from loguru import logger

from app.cli.temporal.models.webhooks.invoice import InvoiceWebhookType
from app.cli.temporal.starter import trigger_workflow
from app.core.cli_settings import WorkerQueues
from app.core.connections import get_lago_webhook_public_key
from app.core.ijson import ijson_loads
from app.models.product import ProductEnum

router = APIRouter()

LAGO_INTERNAL_URL = "lago-api.lago.svc.cluster.local:3000"


def get_issuers(product: ProductEnum) -> list[str]:
    """
    Get the issuer for the product
    """
    app_config = ProductEnum.get_product_settings(product)
    parsed_api_url = urlparse(app_config.lago.api_url)

    base_url = f"{parsed_api_url.scheme}://{parsed_api_url.netloc}"
    return [parsed_api_url.netloc, base_url, LAGO_INTERNAL_URL, f"http://{LAGO_INTERNAL_URL}"]


def validate_issuer(request: Request, issuers: list[str], pub_key: bytes) -> dict:
    """
    Validate the issuer of the webhook and return the event if valid.
    """
    for issuer in issuers:
        try:
            decoded_signature = jwt.decode(
                request.headers.get("X-Lago-Signature"),
                pub_key,
                algorithms=["RS256"],
                issuer=issuer,
            )
            logger.info(f"Valid issuer {issuer}")
            return ijson_loads(decoded_signature["data"])
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token error {issuer}: {e!r}")
    raise HTTPException(status_code=500, detail="Error while decoding JWT signature")


@router.post(
    "/{product}/events",
    operation_id="billingWebhookEvents",
    summary="create customer namespace and setup",
)
async def events_webhook(request: Request, product: ProductEnum = Path(...)) -> None:
    """
    @param request:
    @return:
    """
    pub_key = get_lago_webhook_public_key(product)
    issuers = get_issuers(product)
    logger.info(f"Lago-Signature: {request.headers.get('X-Lago-Signature')}")
    event = validate_issuer(request, issuers, pub_key)
    if event.get("webhook_type") in InvoiceWebhookType:
        from app.cli.temporal.workflows.webhooks.invoice import InvoiceWebhookEvent, InvoiceWebhookEventWorkflow

        arg = InvoiceWebhookEvent.model_validate(event | {"product": product})
        await trigger_workflow(arg, InvoiceWebhookEventWorkflow, WorkerQueues.webhooks)
