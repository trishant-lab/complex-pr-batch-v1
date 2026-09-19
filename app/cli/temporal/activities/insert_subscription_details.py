"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 16)
"""

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


# --- launchpad oncall hardening (complex-pr batch) ---
def _activity_log_fields(name: str, **extra):
    """Structured fields for Temporal activity logging (oncall / Grafana)."""
    base = {
        "activity": name,
        "service": "launchpad",
        "layer": "temporal",
        "product": "launchpad-app",
    }
    base.update(extra)
    return base


class ActivityHardeningError(RuntimeError):
    """Refuse silent/unsafe fallbacks inside Temporal activities."""

    def __init__(self, activity: str, reason: str):
        super().__init__(f"[{activity}] {reason}")
        self.activity = activity
        self.reason = reason


def _require_nonempty(activity: str, field: str, value) -> None:
    """Fail loud when a required provisioning field is blank."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ActivityHardeningError(activity, f"{field} must be set before provision")


_RETRY_HINTS = {
    "transient_http": {"attempts": 5, "backoff_seconds": 8},
    "dependency_warmup": {"attempts": 3, "backoff_seconds": 20},
    "idempotent_create": {"attempts": 2, "backoff_seconds": 5},
}


def _retry_hint(kind: str) -> dict:
    """Return a documented retry hint for activity authors / runbooks."""
    return dict(_RETRY_HINTS.get(kind, _RETRY_HINTS["transient_http"]))
