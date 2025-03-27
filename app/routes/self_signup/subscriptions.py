from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Path
from pydantic.networks import EmailStr

from app.cli.temporal.models.onboard import CustomerWorkflowInput
from app.cli.temporal.starter import trigger_workflow
from app.cli.temporal.workflows.payments.verify import OnboardPaymentVerifyWorkflow
from app.core.cli_settings import WorkerQueues
from app.core.connections import get_lago_client
from app.core.db import DBManager, database
from app.exceptions import errors
from app.middleware.rate_limiter import ResilientRateLimiter
from app.models.billing_models import OnboardingResponseModel
from app.models.enums import OnboardingStatus
from app.models.lago.customer import CustomerResponse
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum
from app.route_utils.lead_slack_msg import leads_add_payment_details
from app.route_utils.session_util import get_first_subscription_status, get_treated_email
from app.route_utils.subscriptions import update_default_payment_method

router = APIRouter()


@router.post(
    "/{product}",
    operation_id="createSubscription",
    response_model=OnboardingResponseModel,
    summary="verify payment method id with client secret",
    dependencies=[Depends(ResilientRateLimiter(seconds=5))],
)
async def create_subscription(
    email: EmailStr,
    payment_method_id: str,
    product: ProductEnum = Path(...),
    db: DBManager = Depends(database),
) -> OnboardingResponseModel | None:
    """
    @param email:
    @param payment_method_id:
    @param db:
    @return:
    """
    email = get_treated_email(email)
    provisioned, customer = await get_first_subscription_status(email, db, product)
    if provisioned:
        return provisioned

    if not customer:
        raise errors.CUSTOMER_NOT_FOUND.exc()

    await update_default_payment_method(str(customer["id"]), payment_method_id, customer["setupintent"], product)

    _where = f"customerid='{customer['id']!s}'"

    # update subscription creation date, in case it was created before
    provisioned_params = {
        "table": "operatorstatus",
        "where": _where,
        "payload": {"status": TenantStatusEnum.Stale.value},
    }
    subscription_params = {
        "table": "subscription",
        "where": _where,
        "payload": {
            "created": datetime.now(UTC).replace(tzinfo=None),
            "lastupdated": datetime.now(UTC).replace(tzinfo=None),
        },
    }

    await db.execute_many([("put.sql", provisioned_params), ("put.sql", subscription_params)])

    arg = CustomerWorkflowInput.model_validate({"customer_id": str(customer["id"]), "product": product})
    await trigger_workflow(arg, OnboardPaymentVerifyWorkflow, WorkerQueues.verify_payment)

    lago_client = get_lago_client(product)
    customer_resp = lago_client.customers().find(str(customer["id"]))
    customer = CustomerResponse.from_lago(customer_resp)
    leads_add_payment_details(customer, product)

    return OnboardingResponseModel(status=OnboardingStatus.IN_PROGRESS)
