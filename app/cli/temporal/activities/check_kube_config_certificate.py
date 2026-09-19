"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 3)
"""

from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.activity_utils.check_kube_config_certificate import check_kube_config_certificate_expiry
from app.cli.temporal.core.base import Activity


class KubeConfigCertExpiryActivity(Activity):
    @staticmethod
    def get_timeout() -> timedelta:
        """
        @return:
        """
        return timedelta(seconds=10)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        @return:
        """
        return RetryPolicy(maximum_attempts=4, maximum_interval=timedelta(seconds=10))

    @staticmethod
    @activity.defn(name="KubeConfigCertExpiryActivity")
    async def defn(activity_input: None) -> None:
        """
        activity to check kube config certificate expiry and send mail if it is expired within one week
        """
        await check_kube_config_certificate_expiry()


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
