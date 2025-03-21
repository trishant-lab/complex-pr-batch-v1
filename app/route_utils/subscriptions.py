from datetime import UTC, datetime
from uuid import UUID

import stripe
from asyncpg import Record
from loguru import logger

from app.core.connections import get_lago_client
from app.core.db import DBManager, get_db_manager
from app.exceptions import errors
from app.models.billing_models import SubscriptionModel
from app.models.lago.customer import CustomerResponse
from app.models.lago.subscription import Subscription
from app.models.product import ProductEnum


async def create_setup_intent(external_id: str, intent_id: str, product: ProductEnum) -> stripe.SetupIntent:
    """
    @param external_id:
    @param intent_id:
    @return:
    create and save intent
    """
    stripe_secret_key = ProductEnum.get_stripe_secret_key(product)
    intent = await stripe.SetupIntent.create_async(
        idempotency_key=intent_id,
        api_key=stripe_secret_key,
        customer=external_id,
        payment_method_types=["card"],
    )
    return await stripe.SetupIntent.retrieve_async(
        id=intent.id,
        api_key=stripe_secret_key,
    )


async def update_default_payment_method(
    customer_id: str, payment_method: str, setupintent: UUID, product: ProductEnum
) -> None:
    """
    verifying payment method id with setupIntent's payment method
    """
    lago_client = get_lago_client(product)
    stripe_secret_key = ProductEnum.get_stripe_secret_key(product)
    customer_resp = lago_client.customers().find(customer_id)
    customer = CustomerResponse.from_lago(customer_resp)
    intent = await create_setup_intent(customer.billing_configuration.provider_customer_id, str(setupintent), product)
    if intent.status not in {"success", "succeeded"} or intent.payment_method != payment_method:
        raise errors.PAYMENT_METHOD_NOT_ADDED.exc()
    try:
        stripe.Customer.retrieve_payment_method(
            intent.customer,
            intent.payment_method,
            api_key=stripe_secret_key,
        )
    except stripe.error.InvalidRequestError as e:
        logger.error(e)
        raise errors.PAYMENT_METHOD_NOT_ADDED.exc()
    stripe.Customer.modify(
        intent.customer,
        invoice_settings={"default_payment_method": intent.payment_method},
        api_key=stripe_secret_key,
    )


async def insert_subscription(
    plan_code: str,
    customer_id: str,
    db: DBManager,
) -> Record:
    """
    @param plan_code:
    @param customer_id:
    @param db:
    @return:
    """
    params = {
        "table": "subscription",
        "payload": {"planCode": plan_code, "customerid": customer_id},
        "returning": ["id"],
    }
    return await db.fetch_one("post.sql", **params)


async def create_subscription_object(subscription: SubscriptionModel) -> Subscription:
    """
    @param subscription:
    @return:
    """
    _subscription = Subscription(
        **subscription.model_dump(exclude={"email", "payment_method_id", "subscription_at"}),
    )
    _subscription.subscription_at = datetime.now(UTC).replace(tzinfo=None).__str__()
    if not _subscription.external_id:
        db: DBManager = await get_db_manager()
        _subscription.external_id = await insert_subscription(
            subscription.plan_code,
            subscription.external_customer_id,
            db,
        )
    return _subscription
