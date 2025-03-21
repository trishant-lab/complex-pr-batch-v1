from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, Path, Query
from pydantic import EmailStr
from starlette.status import HTTP_200_OK

from app.cli.activity_utils.onboard.invoice import fetch_subscription_invoice
from app.cli.activity_utils.onboard.onboard_info import get_customer_onboard_info
from app.core.db import DBManager, get_db_manager
from app.exceptions import errors
from app.models.billing_models import OnboardingResponseModel, OnboardingStage
from app.models.enums import OnboardingStatus
from app.models.input_param_patterns import TOKEN_PATTERN
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum
from app.route_utils.session_util import get_treated_email
from app.route_utils.user_session import UserSession

if TYPE_CHECKING:
    from app.cli.temporal.models.onboard import OnboardInfo

router = APIRouter()


@router.get(
    "/{product}/status",
    operation_id="getProvisioningStatus",
    response_model=OnboardingResponseModel,
    status_code=HTTP_200_OK,
    summary="Get provisioning status of a customer",
)
async def get_provisioning_status(
    email: EmailStr,
    product: ProductEnum = Path(...),
    customer_id: UUID = Query(..., alias="customerId"),
    token: str = Query(..., regex=TOKEN_PATTERN),
) -> OnboardingResponseModel:
    """
    Return ProvisioningStatus
    """
    email = get_treated_email(email)
    await UserSession.validate_session(product=product, email=email, session_token=token)

    db: DBManager = await get_db_manager()
    customer_params = {
        "table": "customer c",
        "where": f"c.email='{email}' AND c.product='{product.value}'",
        "columns": ["c.id"],
    }
    customer_record = await db.fetch_one("get.sql", **customer_params)
    if not customer_record:
        raise errors.CUSTOMER_NOT_FOUND.exc()
    if customer_id != customer_record["id"]:
        raise errors.INVALID_REQUEST.exc()

    onboard_info: OnboardInfo = await get_customer_onboard_info(customer_id)
    invoice = fetch_subscription_invoice(onboard_info)
    _response = OnboardingResponseModel(
        onboardingStage=OnboardingStage(
            provisioningStatus=onboard_info.onboard_status,
            invoice=invoice,
            failedInvoiceReason=onboard_info.failed_invoice_reason,
            paymentStatus=invoice.payment_status,
        ),
    )
    match onboard_info.onboard_status:
        case TenantStatusEnum.Provisioned:
            _response.status = OnboardingStatus.PROVISIONED
        case _:
            _response.status = OnboardingStatus.IN_PROGRESS
    return _response
