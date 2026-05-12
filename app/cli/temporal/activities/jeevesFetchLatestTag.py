"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 20)
"""

import re
from datetime import timedelta

import httpx
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity
from app.cli.temporal.core.log import log_error
from app.core.settings import AppSettings, get_settings


class JeevesFetchLatestTagActivity(Activity):
    """
    JeevesFetchLatestTagActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(minutes=10)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), maximum_attempts=1, backoff_coefficient=3)

    @staticmethod
    @activity.defn(name="JeevesFetchLatestTagActivity")
    async def defn() -> str:
        """
        Fetch latest tags
        """
        config: AppSettings = get_settings()
        url = f"{config.docker_registry.registry_url}/v2/jeeves-app/tags/list"
        try:
            response = httpx.get(
                url, auth=(config.docker_registry.registry_username, config.docker_registry.registry_password)
            )
            if response.is_success:
                tags = response.json().get("tags", [])
                pattern = r"^jeeves-[\d\.]+$"
                filtered_tags = sorted(tag for tag in tags if re.match(pattern, tag))
                return filtered_tags[-1] if filtered_tags else "production"
            response.raise_for_status()
        except Exception as e:
            log_error(f"Error fetching latest tag: {e=}")
        return "production"


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
