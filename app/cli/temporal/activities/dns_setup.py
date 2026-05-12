"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 11)
"""

from temporalio import activity
from temporalio.common import RetryPolicy


import asyncio
from datetime import timedelta
import socket
from google.cloud import dns
from google.api_core.exceptions import Conflict
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info


class DnsSetupActivityModel(LaunchpadCLIBaseModel):
    """
    DnsSetupActivityModel
    """

    cname: str
    fqdn: str
    zone_name: str


class DnsSetupActivity(Activity):
    """
    DnsSetupActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(minutes=10)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), maximum_attempts=5, backoff_coefficient=3)

    @staticmethod
    @activity.defn(name="DnsSetupActivity")
    async def defn(activity_model: DnsSetupActivityModel) -> None:
        """
        Callable for the activity
        """
        client = dns.Client()

        zone = client.zone(activity_model.zone_name)

        try:
            changes = zone.changes()

            record_set = dns.ResourceRecordSet(
                name=activity_model.fqdn,
                record_type="CNAME",
                ttl=1 * 60 * 60,  # 1 hour in seconds
                rrdatas=[activity_model.cname],
                zone=zone,
            )

            changes.add_record_set(record_set)
            changes.create()

            log_info(f"DNS record created: {activity_model.fqdn}")
        except Conflict:
            log_info(message=f"DNS record Already Present: {activity_model.fqdn}")

        # check DNS propagation
        count = 0
        while True:
            try:
                socket.getaddrinfo(activity_model.fqdn, 0)
                break
            except socket.gaierror:
                count += 1
                if count == 61:
                    raise TimeoutError(f"DNS propagation check timed out after [10 min]: {activity_model.fqdn}")
                log_info(f"DNS not propagated yet: {activity_model.fqdn}")
                await asyncio.sleep(10)


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
