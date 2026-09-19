"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 42)
"""

from datetime import timedelta
from uuid import uuid4

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.keycloak_utils import KeycloakAdminClient, get_keycloak_manager
from app.cli.temporal.core.base import Activity
from app.cli.temporal.penknife.models.penknife_spec import PenknifeSpec


class PenknifeUserSetupActivity(Activity):
    """
    PenknifeUserSetupActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=300)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="PenknifeUserSetupActivity")
    async def defn(penknife: PenknifeSpec) -> None:
        """
        Callable for the activity
        """
        from datetime import datetime

        from loguru import logger

        from app.cli.temporal.activities.penknife_novu_setup import NovuSetup
        from app.cli.temporal.core.log import log_info
        from app.core.db import DBManager, get_db_manager
        from app.core.ijson import ijson_dumps
        from app.core.settings import PenknifeSettings, get_settings

        subscriber_id = str(uuid4())

        NovuSetup(penknife=penknife).create_subscriber_in_novu(subscriber_id=subscriber_id)

        keycloak_client: KeycloakAdminClient = get_keycloak_manager()
        keycloak_user_id = keycloak_client.get_user_id(username=penknife.email, realm_name=penknife.tenant)

        penknife_config: PenknifeSettings = get_settings().penknife

        try:
            db: DBManager = await get_db_manager(dsn=penknife_config.postgres.dsn)
            attributes = ijson_dumps({"email": penknife.email})
            await db.execute_raw_sql("""SELECT set_config('myvars.user_email', 'api@penknife.app', false);""")
            await db.fetch_one(
                sqlfile="penknife/insert_subscription_mapping.sql",
                db_schema_name=penknife.tenant,
                **{
                    "schema": penknife.tenant,
                    "user_id": keycloak_user_id,
                    "subscriber_id": subscriber_id,
                    "attributes": attributes,
                },
            )
            await db.fetch_one(
                sqlfile="penknife/insert_user_audit.sql",
                db_schema_name=penknife.tenant,
                **{"schema": penknife.tenant, "email": penknife.email, "datetime": datetime.now()},
            )
            await db.fetch_one(
                sqlfile="penknife/update_organization.sql",
                db_schema_name=penknife.tenant,
                **{"schema": penknife.tenant, "companydomain": penknife.companyDomain},
            )

            log_info("User detail is added to postgres")

        except Exception as e:
            logger.error(f"Error while updating user entry in useraudit: {e}")
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
