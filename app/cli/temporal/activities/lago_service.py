import uuid
import lago_python_client

from datetime import datetime
from datetime import timedelta
from temporalio.common import RetryPolicy
from temporalio import activity

from app.cli.temporal.core.base import LaunchpadCLIBaseModel, Activity
from lago_python_client.exceptions import LagoApiError
from lago_python_client.models import Customer, Subscription
from app.cli.temporal.core.log import log_info, log_error

LIVE_SUBSCRIPTION_STATUSES = frozenset({"active", "pending"})


class LagoProperties(LaunchpadCLIBaseModel):
    tenant: str
    customer_id: uuid.UUID
    customer_name: str
    customer_email: str
    subscription_id: uuid.UUID
    plan_code: str
    api_key: str
    api_url: str


def get_lago_client(properties: LagoProperties) -> lago_python_client.Client:
    """Initialize and return a Lago API client."""
    return lago_python_client.Client(
        api_key=properties.api_key,
        api_url=properties.api_url,
    )


def create_new_customer(properties: LagoProperties) -> bool:
    """Create a new customer in Lago using the specified properties."""
    customer = Customer(
        name=properties.customer_name,
        legal_name=properties.customer_name,
        firstname=properties.customer_name,
        email=properties.customer_email,
        external_id=str(properties.customer_id),
        finalize_zero_amount_invoice="inherit",
    )
    log_info(f"Creating new customer with tenant '{properties.tenant}' and ID '{properties.customer_id}'")
    try:
        client = get_lago_client(properties)
        response = client.customers().create(customer)
        log_info(f"Customer '{properties.tenant}' created successfully with response: {response}")
        return True
    except LagoApiError as e:
        log_error(f"Failed to create customer '{properties.tenant}': Status Code {e.status_code}")
        log_error(f"API Response: {e.response}")
        return False


def find_existing_subscription(properties: LagoProperties) -> str | None:
    """Return the external id of a subscription the customer already holds, if any.

    Onboarding is a one-time setup and tenant names cannot be reused, so a customer that
    already carries a subscription means this is a retry of an earlier run rather than a
    plan change. Creating a second one would bill the tenant twice.

    A Lago failure is left to propagate: retrying the activity is safe, whereas treating an
    unreachable API as "no subscription exists" is exactly how the duplicates appear.
    """
    client = get_lago_client(properties)
    response = client.subscriptions().find_all({"external_customer_id": str(properties.customer_id)})
    for subscription in response.get("subscriptions", []):
        if subscription.status in LIVE_SUBSCRIPTION_STATUSES:
            return subscription.external_id
    return None


def create_subscription(properties: LagoProperties) -> bool:
    """Create a new subscription in Lago for the specified customer."""
    # Prepare subscription data
    subscription = Subscription(
        external_customer_id=str(properties.customer_id),
        plan_code=properties.plan_code,
        subscription_at=datetime.now().isoformat(),
        external_id=str(properties.subscription_id),
    )
    log_info(
        f"Creating subscription with ID '{properties.subscription_id}' for customer "
        f"{properties.customer_id} using plan '{properties.plan_code}'"
    )
    try:
        client = get_lago_client(properties)
        response = client.subscriptions().create(subscription)
        log_info(f"Subscription '{properties.subscription_id}' created successfully with response: {response}")
        return True
    except LagoApiError as e:
        log_error(
            f"Failed to create subscription '{properties.subscription_id}' "
            f"for customer '{properties.customer_id}': Status Code {e.status_code}"
        )
        log_error(f"API Response: {e.response}")
        return False


class LagoSetupActivity(Activity):
    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="LagoSetupActivity")
    async def defn(properties: LagoProperties) -> None:
        """
        Main activity method to set up Lago by creating a new customer and subscription.
        """
        log_info("Starting Lago setup activity.")
        # Step 1: Create new customer
        customer_created = create_new_customer(properties)
        if not customer_created:
            log_error(f"Failed to create customer '{properties.customer_id}' for tenant '{properties.tenant}'")
            raise RuntimeError(
                f"Lago customer creation failed for customer '{properties.customer_id}' on tenant '{properties.tenant}'"
            )
        # Step 2: Create subscription for the customer, unless one is already in place
        existing_subscription = find_existing_subscription(properties)
        if existing_subscription:
            log_info(
                f"Customer '{properties.customer_id}' already holds subscription '{existing_subscription}'; "
                f"skipping subscription creation"
            )
        else:
            subscription_created = create_subscription(properties)
            if not subscription_created:
                log_error(
                    f"Failed to create subscription '{properties.subscription_id}' "
                    f"for customer '{properties.customer_id}'"
                )
                raise RuntimeError(
                    f"Lago subscription creation failed for subscription '{properties.subscription_id}' "
                    f"on customer '{properties.customer_id}'"
                )
        log_info(
            f"Lago setup completed successfully for tenant '{properties.tenant}' "
            f"with customer ID '{properties.customer_id}'"
        )
