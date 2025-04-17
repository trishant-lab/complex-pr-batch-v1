from urllib.parse import urlparse

import jwt
from fastapi import APIRouter, Path, Request

from app.cli.temporal.models.webhooks.invoice import InvoiceWebhookType
from app.cli.temporal.starter import trigger_workflow
from app.core.cli_settings import WorkerQueues
from app.core.connections import get_lago_webhook_public_key
from app.core.ijson import ijson_loads
from app.models.product import ProductEnum

router = APIRouter()


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
    app_config = ProductEnum.get_product_settings(product)
    decoded_signature = jwt.decode(
        request.headers.get("X-Lago-Signature"),
        pub_key,
        algorithms=["RS256"],
        issuer=urlparse(app_config.lago.api_url).netloc,
    )
    event = ijson_loads(decoded_signature["data"])
    if event.get("webhook_type") in InvoiceWebhookType:
        from app.cli.temporal.workflows.webhooks.invoice import InvoiceWebhookEvent, InvoiceWebhookEventWorkflow

        arg = InvoiceWebhookEvent.model_validate(event | {"product": product})
        await trigger_workflow(arg, InvoiceWebhookEventWorkflow, WorkerQueues.webhooks)
