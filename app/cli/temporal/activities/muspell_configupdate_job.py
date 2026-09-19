"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 30)
"""

import json
from datetime import timedelta

from pydantic_core import MultiHostUrl
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info
from app.core.db import get_db_manager
from app.core.settings import AppSettings, get_settings


class MuspellConfigUpdateJobActivityModel(LaunchpadCLIBaseModel):
    """
    Seeds the new-shape muspell-archive config for a tenant:
      * `systems` — one row per onboarded application for the `system` table
        (each dict: system_id, name, display_name, database, mnemonic,
        search_identifiers). The `system_id` is the same UUID used to key the
        Keycloak `applicationaccess` attribute.
    The schema + config rows themselves are created and default-seeded by
    muspell-archive's dbmate baseline on first boot; everything else
    (organization globals incl. enable_mpi, column, dataFlag, …) stays
    baseline-default — onboarding does not touch them.
    """

    systems: list[dict]
    schema_name: str
    database_name: str
    username: str
    password: str


class MuspellConfigUpdateJobActivity(Activity):
    """
    Inserts the tenant's `system` rows (uuid-keyed, matching the Keycloak
    applicationaccess). No other config is touched (baseline defaults apply).
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity. Also the backstop for a dbmate race: if the
        `system` table isn't created yet, the INSERT errors and the activity
        retries with backoff.
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="MuspellConfigUpdateJobActivity")
    async def defn(activity_model: MuspellConfigUpdateJobActivityModel) -> dict[str, str]:
        """
        Seed the `system` table for the tenant (one row per onboarded application)
        and return a `{name: id}` map of the **canonical** ids the DB ended up with.

        Why return the map: insert_system.sql is `ON CONFLICT (name) DO UPDATE` which
        preserves the row's existing id. The candidate `system["system_id"]` the
        workflow mints via `workflow.uuid4()` is therefore only authoritative for
        rows the activity newly inserts — on conflict the existing id wins. The
        workflow uses the returned map to keep Keycloak applicationaccess keyed by
        the DB's stable ids across re-runs (otherwise the two drift apart).
        """
        config: AppSettings = get_settings()

        pg_dsn = MultiHostUrl(
            f"postgres://{activity_model.username}:{activity_model.password}@{config.postgres.host}:{config.postgres.port}/{activity_model.database_name}"
        )
        db_manager = await get_db_manager(pg_dsn)

        # Each insert runs in its own transaction (no cross-row atomicity); re-run
        # and partial-failure safety relies on insert_system.sql's
        # `ON CONFLICT (name) DO UPDATE` (keeps the existing id) — do not drop it.
        # `RETURNING id, name` lets us capture either the inserted candidate id or
        # the conflict-row's preserved id without a second SELECT.
        canonical_systems: dict[str, str] = {}
        for system in activity_model.systems:
            row = await db_manager.fetch_one(
                sqlfile="muspell/insert_system.sql",
                db_schema_name=activity_model.schema_name,
                system_id=system["system_id"],
                name=system["name"],
                display=system["display_name"],
                database=system["database"],
                mnemonic=system["mnemonic"],
                search_identifiers=json.dumps(system["search_identifiers"]),
            )
            canonical_systems[row["name"]] = str(row["id"])

        log_info(f"Seeded {len(canonical_systems)} system row(s) for {activity_model.schema_name}.")
        return canonical_systems


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
