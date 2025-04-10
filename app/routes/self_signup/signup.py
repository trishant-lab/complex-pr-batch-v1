import uuid
from collections import OrderedDict
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Path, Query
from lago_python_client.exceptions import LagoApiError
from loguru import logger
from pydantic import ValidationError

from app.cli.temporal.models.onboard import CustomerWorkflowInput
from app.cli.temporal.starter import trigger_workflow
from app.cli.temporal.workflows.payments.verify import OnboardPaymentVerifyWorkflow
from app.core.cli_settings import WorkerQueues
from app.core.connections import get_lago_client
from app.core.db import DBManager, database
from app.core.ijson import ijson_dumps, ijson_loads
from app.core.oauth2 import get_oauth_scheme
from app.exceptions import errors
from app.models.billing_models import CustomerModel, CustomerResponseModel, OnboardingResponseModel
from app.models.input_param_patterns import TOKEN_PATTERN
from app.models.lago.customer import Customer, CustomerResponse
from app.models.product import ProductEnum
from app.models.tenant import TenantStatusEnum
from app.route_utils.account_management import update_customer_model
from app.route_utils.coupon import apply_coupon, get_coupon_by_code
from app.route_utils.lead_slack_msg import leads_form_fill
from app.route_utils.plans_util import verify_active_plan_codes, verify_enterprise_plans
from app.route_utils.product import validate_email_domain, validate_provisioning_details
from app.route_utils.session_util import get_first_subscription_status, get_treated_email
from app.route_utils.subscriptions import create_setup_intent
from app.route_utils.tenant_suggestions import get_existing_tenant_names
from app.route_utils.user_session import UserSession
from app.routes.self_signup.subscriptions import _create_subscription

if TYPE_CHECKING:
    from app.models.lago.coupon import CouponResponse

router = APIRouter()


ACTIVE_SUBSCRIPTION_NAME: str = "Active Subscription"


async def reconcile_subscription(
    db: DBManager,
    customer: CustomerModel,
    customer_id: uuid.UUID,
    subscription_plan: str,
    product: ProductEnum,
) -> None:
    """
    Terminate failed subscription of a customer
    """
    customer_params = {
        "table": "customer",
        "payload": {
            "tenantname": customer.tenant.lower(),
            "orgname": customer.legal_name,
        },
        "where": f"email='{customer.email!s}' AND product='{product.value.lower()}'",
    }
    queries = [
        ("put.sql", customer_params),
    ]

    existing_invoice_params = dict(table="failedinvoices", where=f"customerid='{customer_id!s}'")
    failed_invoice = await db.fetch_one("get.sql", **existing_invoice_params)
    if failed_invoice:
        delete_subs_params = {
            "table": "subscription",
            "where": f"id='{failed_invoice['subscriptionid']!s}'",
        }
        create_subs_params = {
            "table": "subscription",
            "payload": OrderedDict(
                {
                    "name": "Active Subscription",
                    "plancode": subscription_plan,
                    "product": product.value.lower(),
                    "customerid": str(customer_id),
                }
            ),
            "returning": ["id"],
        }

        # delete failed subscription and create new one
        queries.extend(
            [
                ("delete.sql", delete_subs_params),
                ("delete.sql", existing_invoice_params),
                ("post.sql", create_subs_params),
            ]
        )
    else:
        # update subscription to new plan
        subscription_params = {
            "table": "subscription",
            "payload": {"name": ACTIVE_SUBSCRIPTION_NAME, "plancode": subscription_plan},
            "where": f"customerid='{customer_id!s}'",
        }
        queries.append(("put.sql", subscription_params))
    await db.execute_many(queries)


async def update_existing_customer(
    customer_record: dict,
    customer: CustomerModel,
    plan_code: str,
    product: ProductEnum,
    db: DBManager,
) -> tuple[OnboardingResponseModel, CustomerResponse]:
    """
    find lago customer, check its intent status.
    If intent is successful, trigger provisioning
    """
    await reconcile_subscription(db, customer, customer_record["id"], plan_code, product)

    customer.external_id = str(customer_record["id"])

    lago_client = get_lago_client(product)
    lago_customer_resp = lago_client.customers().find(customer.external_id)
    lago_customer = CustomerResponse.from_lago(lago_customer_resp)
    updated_customer = update_customer_model(
        CustomerModel.model_validate(
            lago_customer.model_dump(exclude_unset=True) | {"product": product.value, "tenant": customer.tenant}
        ),
        customer,
    )

    try:
        customer = lago_client.customers().create(Customer.model_validate(updated_customer))
    except LagoApiError as e:
        logger.error(e.status_code)
        logger.error(e.response)
        raise errors.INVALID_VALUES.exc()

    intent = await create_setup_intent(
        lago_customer.billing_configuration.provider_customer_id,
        customer_record["setupintent"],
        product,
    )
    if intent.status in {"success", "succeeded"}:
        return (
            await _create_subscription(
                product=product, email=customer.email, payment_method_id=intent.payment_method, db=db
            ),
            lago_customer,
        )
    # update if setup intent is canceled
    return OnboardingResponseModel(clientSecret=intent.client_secret), lago_customer


async def create_new_customer(
    customer: CustomerModel,
    form_data: dict,
    plan_code: str,
    product: ProductEnum,
    db: DBManager,
) -> tuple[OnboardingResponseModel, CustomerResponse]:
    """

    @param customer:
    @param plan_code:
    @param db:
    @return:
    creating customer, setup intent creation needs stripe customer id (created by lago)
    """
    idempotency_key = str(uuid.uuid4())

    customer_params = {
        "tenantname": customer.tenant.lower(),
        "setupintent": idempotency_key,
        "email": customer.email,
        "orgname": customer.legal_name,
        "product": product.value,
        "data": ijson_dumps(form_data),
    }
    subscription_params = {
        "name": ACTIVE_SUBSCRIPTION_NAME,
        "plancode": plan_code,
    }
    provisioningstatus_params = {
        "status": TenantStatusEnum.NotApplicable,
        "errors": ijson_dumps({"error": "NA"}),
    }
    customer_insert = await db.fetch_one(
        "post_customer_subscription_provisioningstatus.sql",
        customer=customer_params,
        subscription=subscription_params,
        provisioningstatus=provisioningstatus_params,
    )
    customer.external_id = str(customer_insert["customerid"])
    lago_client = get_lago_client(product)
    try:
        customer = lago_client.customers().create(Customer.model_validate(customer))
    except LagoApiError as e:
        logger.error(e.status_code)
        logger.error(e.response)
        raise errors.INVALID_VALUES.exc()

    intent = await create_setup_intent(
        customer.billing_configuration.provider_customer_id,
        idempotency_key,
        product,
    )

    lago_customer_resp = lago_client.customers().find(customer.external_id)
    lago_customer = CustomerResponse.from_lago(lago_customer_resp)
    return OnboardingResponseModel(clientSecret=intent.client_secret), lago_customer


@router.post(
    "/{product}",
    operation_id="signUp",
    response_model=OnboardingResponseModel,
    summary="create customer",
)
async def create_customer(
    signup_details: dict,
    product: ProductEnum = Path(...),
    plan_code: str = Query(...),
    token: str = Query(..., regex=TOKEN_PATTERN),
    db: DBManager = Depends(database),
) -> OnboardingResponseModel:
    """
    @param customer:
    @param plan_code:
    @param token:
    @param db:
    @return:
    """
    customer = await validate_provisioning_details(product=product, data=signup_details)
    customer.email = get_treated_email(customer.email)
    validate_email_domain(product=product, email=customer.email)
    await UserSession.validate_session(product=product, email=customer.email, session_token=token)
    coupon: CouponResponse | None = None
    if customer.couponCode:
        coupon = get_coupon_by_code(customer.couponCode, product)
    provisioned, customer_record = await get_first_subscription_status(customer.email, db, product)
    if provisioned:
        return provisioned

    verify_active_plan_codes(product, plan_code)
    tenant_names = await get_existing_tenant_names(
        product,
        customer.email,
        [customer.tenant.lower()],
    )
    if tenant_names:
        raise errors.ALREADY_ALLOCATED_TENANT_NAME.exc()

    try:
        customer_data = customer.model_dump()
        customer = CustomerModel.model_validate(
            customer_data
            | {
                "legal_name": customer.organization,
                "name": customer.firstName + " " + customer.lastName,
                "product": product.value,
                "address_line1": customer.address,
            }
        )
    except ValidationError as e:
        logger.error(f"Invalid schema: {e.errors()}")
        raise errors.INVALID_SCHEMA.exc()

    if customer_record:
        response, lago_customer = await update_existing_customer(customer_record, customer, plan_code, product, db)
    else:
        response, lago_customer = await create_new_customer(customer, signup_details, plan_code, product, db)

    if coupon:
        apply_coupon(lago_customer.external_id, coupon, product)

    leads_form_fill(lago_customer, product)
    _customer_response = ijson_loads(lago_customer.model_dump_json(exclude={"billing_configuration"})) | dict(
        tenant_name=customer.tenant,
        email=customer.email,
        plancode=plan_code,
    )
    response.customer = CustomerResponseModel.model_validate(_customer_response)
    return response


@router.post(
    "/{product}/enterprise",
    operation_id="enterpriseSignUp",
    summary="create enterprise customer",
)
async def create_enterprise_customer(
    signup_details: dict,
    product: ProductEnum = Path(...),
    plan_code: str = Query(default="ee_m_v1"),
    db: DBManager = Depends(database),
    _: dict = Depends(get_oauth_scheme()),
) -> None:
    """
    @param customer:
    @param plan_code:
    @param db:
    @return:
    """
    customer = await validate_provisioning_details(product=product, data=signup_details)
    validate_email_domain(product=product, email=customer.email)
    tenant_names = await get_existing_tenant_names(
        product,
        customer.email,
        [customer.tenant.lower()],
    )
    await verify_enterprise_plans(product, plan_code)
    if tenant_names:
        raise errors.ALREADY_ALLOCATED_TENANT_NAME.exc()

    try:
        customer_data = customer.model_dump()
        customer = CustomerModel.model_validate(
            customer_data
            | {
                "legal_name": customer.organization,
                "name": customer.firstName + " " + customer.lastName,
                "product": product.value,
                "address_line1": customer.address,
            }
        )
    except ValidationError as e:
        logger.error(f"Invalid schema: {e.errors()}")
        raise errors.INVALID_SCHEMA.exc()

    customer_params = {
        "tenantname": customer.tenant.lower(),
        "setupintent": str(uuid.uuid4()),
        "email": customer.email,
        "orgname": customer.legal_name,
        "product": product.value,
        "data": ijson_dumps(signup_details),
    }
    subscription_params = {
        "name": ACTIVE_SUBSCRIPTION_NAME,
        "plancode": plan_code,
    }
    provisioningstatus_params = {
        "status": TenantStatusEnum.NotApplicable,
        "errors": ijson_dumps({"error": "NA"}),
    }
    customer_insert = await db.fetch_one(
        "post_customer_subscription_provisioningstatus.sql",
        customer=customer_params,
        subscription=subscription_params,
        provisioningstatus=provisioningstatus_params,
    )

    customer.external_id = str(customer_insert["customerid"])
    lago_client = get_lago_client(product)
    try:
        lago_client.customers().create(Customer.model_validate(customer))
    except LagoApiError as e:
        logger.error(e.status_code)
        logger.error(e.response)
        raise errors.INVALID_VALUES.exc()

    arg = CustomerWorkflowInput.model_validate({"customer_id": str(customer.external_id), "product": product})
    await trigger_workflow(arg, OnboardPaymentVerifyWorkflow, WorkerQueues.verify_payment)
