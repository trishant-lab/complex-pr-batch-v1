from datetime import timedelta

import pendulum
from lago_python_client.exceptions import LagoApiError
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity
from app.cli.temporal.core.log import log_info
from app.cli.temporal.models.deboard import DeboardWorkflowInput
from app.core.connections import get_lago_client
from app.core.db import get_db_manager
from app.models.lago.subscription import Subscription, SubscriptionResponse


def compute_deprovision_ending_at(current_billing_period_started_at: str) -> str:
    """
    Compute the Lago subscription ``ending_at`` for a deprovisioned tenant.

    The subscription is ended at the close of its current billing period, so the
    tenant is billed for the current period but not the next one. With anniversary
    billing that boundary is one month after the current billing period start,
    minus one day (e.g. a period starting 2026-06-30 ends 2026-07-29).
    """
    period_start = pendulum.parse(current_billing_period_started_at)
    ending_at = period_start.add(months=1).subtract(days=1).end_of("day")
    return ending_at.isoformat()


class UpdateSubscriptionEndDateActivity(Activity):
    """
    Set the Lago subscription end date for a deprovisioned tenant so it is no
    longer billed for the upcoming billing period.
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        @return:
        """
        return timedelta(seconds=30)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        @return:
        """
        return RetryPolicy(
            maximum_attempts=4,
            maximum_interval=timedelta(seconds=10),
            non_retryable_error_types=["NonRetryableException"],
        )

    @staticmethod
    @activity.defn(name="UpdateSubscriptionEndDateActivity")
    async def defn(activity_input: DeboardWorkflowInput) -> None:
        """
        Look up the tenant's active subscription and set its Lago ``ending_at``.
        """
        db = await get_db_manager()
        subscription_row = await db.fetch_one(
            sqlfile="get_active_subscription_by_tenant.sql",
            tenant_name=activity_input.tenant_name,
            product=activity_input.product.value,
        )
        if not subscription_row:
            log_info(
                f"No active subscription found for tenant {activity_input.tenant_name}; skipping Lago end-date update"
            )
            return

        subscription_id = subscription_row["id"]
        lago_client = get_lago_client(activity_input.product)

        try:
            subscription_resp = lago_client.subscriptions().find(str(subscription_id))
        except LagoApiError as e:
            log_info(f"Lago subscription {subscription_id} not found: {e.status_code}")
            return

        subscription_resp = SubscriptionResponse.from_lago(subscription_resp)
        if not subscription_resp:
            return

        if subscription_resp.ending_at:
            log_info(f"Subscription {subscription_id} already has ending_at={subscription_resp.ending_at}; skipping")
            return

        period_start = subscription_resp.current_billing_period_started_at
        if not period_start:
            log_info(
                f"Subscription {subscription_id} has no current billing period start; skipping Lago end-date update"
            )
            return

        ending_at = compute_deprovision_ending_at(period_start)
        subscription: Subscription = Subscription.model_validate(subscription_resp.model_dump())
        subscription.ending_at = ending_at

        try:
            lago_client.subscriptions().update(subscription, identifier=subscription.external_id)
            log_info(f"Set ending_at={ending_at} on Lago subscription {subscription_id}")
        except LagoApiError as e:
            log_info(f"Failed to update Lago subscription {subscription_id}: {e.status_code}")
            raise
