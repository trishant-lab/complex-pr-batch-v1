from datetime import timedelta
from uuid import UUID

from app.core.oauth2 import logger
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
        return timedelta(seconds=30)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
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

        try:
            # First, get customer by email and product
            customer = await db.fetch_one(
                sqlfile="get_tenant_by_name.sql",
                tenant_name=activity_model.tenant_name,
                product=activity_model.product.lower(),
            )

            if not customer:
                logger.error(f"Customer not found for email: {activity_model.email}")

            customer_id = UUID(customer["id"])

            # Insert subscription details
            subscription = await db.fetch_one(
                sqlfile="insert_subscription_details.sql",
                customer_id=str(customer_id),
                name=activity_model.name,
                plancode=activity_model.plan_code,
                product=activity_model.product.lower(),
            )

            subscription_id = UUID(subscription["id"])

            log_info(f"Successfully inserted subscription for customer {customer_id}, subscription {subscription_id}")

            return InsertSubscriptionDetailsActivityResult(
                customer_id=customer_id,
                subscription_id=subscription_id
            )
        except Exception as e:
            log_info(f"Failed to insert subscription details: {str(e)}")
            raise e