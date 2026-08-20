from datetime import timedelta
from uuid import UUID

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info
from app.core.db import get_db_manager


class InsertSubscriptionDetailsActivityModel(LaunchpadCLIBaseModel):
    """
    Model for inserting subscription details
    """

    tenant_name: str
    product: str
    plancode: str
    name: str = "Active Subscription"


class InsertSubscriptionDetailsActivityResult(LaunchpadCLIBaseModel):
    """
    Result model containing customer_id and subscription_id
    """

    customer_id: UUID
    subscription_id: UUID


class InsertSubscriptionDetailsActivity(Activity):
    """
    Activity to retrieve customer by email and insert subscription details
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=30)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=5),
            backoff_coefficient=2,
            maximum_attempts=3,
        )

    @staticmethod
    @activity.defn(name="InsertSubscriptionDetailsActivity")
    async def defn(activity_model: InsertSubscriptionDetailsActivityModel) -> InsertSubscriptionDetailsActivityResult:
        """
        Retrieve customer by email and insert subscription details
        Returns customer_id and subscription_id for Lago setup
        """
        db = await get_db_manager()

        # Resolved outside the try below: a missing customer is a caller error, not something the
        # generic handler should log as an insert failure -- and raising inside that try would just
        # be caught and re-raised by it (ruff TRY301).
        customer = await db.fetch_one(
            sqlfile="get_tenant_by_name.sql",
            tenant_name=activity_model.tenant_name,
            product=activity_model.product.lower(),
        )

        if not customer:
            raise ValueError(f"Customer not found for tenant: {activity_model.tenant_name}")

        customer_id = customer["id"]

        try:
            # Reuse the existing subscription rather than inserting a second one. The row id
            # becomes the Lago subscription's external_id, and Lago creates a new subscription
            # for every external_id it has not seen -- so a fresh id on each retry bills the
            # tenant again. Nothing enforces uniqueness at the table level, so the check lives here.
            existing = await db.fetch_one(
                sqlfile="get_subscription_by_customer.sql",
                customer_id=str(customer_id),
                product=activity_model.product.lower(),
                name=activity_model.name,
            )

            if existing:
                subscription_id = existing["id"]
                log_info(f"Reusing existing subscription {subscription_id} for customer {customer_id}")
            else:
                subscription = await db.fetch_one(
                    sqlfile="insert_subscription_details.sql",
                    customer_id=str(customer_id),
                    name=activity_model.name,
                    plancode=activity_model.plancode,
                    product=activity_model.product.lower(),
                )

                subscription_id = subscription["id"]

                log_info(
                    f"Successfully inserted subscription for customer {customer_id}, subscription {subscription_id}"
                )

            return InsertSubscriptionDetailsActivityResult(customer_id=customer_id, subscription_id=subscription_id)
        except Exception as e:
            log_info(f"Failed to insert subscription details: {e!s}")
            raise e
