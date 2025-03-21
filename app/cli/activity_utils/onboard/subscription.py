import pendulum
from lago_python_client.exceptions import LagoApiError
from loguru import logger

from app.cli.temporal.models.onboard import OnboardInfo
from app.core.connections import get_lago_client
from app.core.db import get_db_manager
from app.models.lago.subscription import Subscription, SubscriptionResponse


def create_lago_subscription(onboard_info: OnboardInfo) -> None:
    """
    Create lago subscription, if not exists
    """
    subs_name = "Active Subscription"
    lago_client = get_lago_client(onboard_info.product)
    # find subscription
    try:
        subscription = lago_client.subscriptions().find(str(onboard_info.subscription_id))
        if subscription:
            return
    except LagoApiError as e:
        logger.warning(e.status_code)
        logger.warning(getattr(e.response, "text", e.response))

    # create if not found
    _subscription = Subscription(
        plan_code=onboard_info.subscription_plan,
        external_customer_id=str(onboard_info.customer_id),
        external_id=str(onboard_info.subscription_id),
        name=subs_name,
        subscription_at=onboard_info.subscription_created.isoformat(),
        billing_time="anniversary",
    )
    try:
        lago_client.subscriptions().create(_subscription)
    except LagoApiError as e:
        logger.error(e.status_code)
        logger.error(getattr(e.response, "text", e.response))
        raise


async def terminate_failed_subscription(onboard_info: OnboardInfo) -> None:
    """
    Recreate failed subscription
    """
    # check by failed invoice id for failed subscription
    # terminate lago subscription with failed invoice id, last date of next month
    # create new subscription id, delete old subscription

    db = await get_db_manager()
    existing_invoice_params = dict(
        table="failedinvoices",
        where=f"customerid='{onboard_info.customer_id!s}'",
    )

    failed_invoice = await db.fetch_one("get.sql", **existing_invoice_params)
    if failed_invoice:
        lago_client = get_lago_client(onboard_info.product)
        subscription_resp = lago_client.subscriptions().find(
            str(failed_invoice["subscriptionid"]),
        )
        subscription_resp = SubscriptionResponse.from_lago(subscription_resp)
        if not subscription_resp.ending_at:
            ending_date = pendulum.parse(subscription_resp.created_at).add(months=1).subtract(days=1).isoformat()
            subscription: Subscription = Subscription.model_validate(subscription_resp)
            subscription.ending_at = ending_date
            try:
                lago_client.subscriptions().update(subscription, identifier=subscription.external_id)
            except LagoApiError as e:
                logger.error(e.status_code)
                logger.error(getattr(e.response, "text", e.response))
                raise
