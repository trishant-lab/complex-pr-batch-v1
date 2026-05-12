"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 66)
"""

import re
from datetime import timedelta

import httpx
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity
from app.cli.temporal.core.log import log_error, log_info
from app.core.settings import AppSettings, get_settings

# release-build.yml validates a release tag as ^[0-9]+\.[0-9]+(\.[0-9]+)?$ and
# publishes it to zsegment-api, zsegment-engine and zsegment-connector at the
# same version.
RELEASE_TAG_PATTERN = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?$")

# Nothing publishes :production for zsegment-api/engine any more - the release
# pipeline replaced it with :<version> and :latest - so a fallback of
# "production" would point a new production tenant at an unmaintained tag.
FALLBACK_TAG = "latest"


class ZsegmentFetchLatestTagActivity(Activity):
    """
    Resolves the newest published release tag for the zsegment images.

    Production tenants used to be provisioned against :production. The integration
    pipeline (ci.yml) only builds on sprint, and the release pipeline publishes
    :<version> plus :latest, so :production is no longer maintained by anything.
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
        return RetryPolicy(initial_interval=timedelta(seconds=10), maximum_attempts=3, backoff_coefficient=3)

    @staticmethod
    def newest_release_tag(tags: list[str]) -> str:
        """
        The highest release tag in `tags`, or the fallback when none is published.

        Ordered on the parsed components rather than the string: sorting
        lexicographically places 1.10.0 before 1.9.0 and would pick the older
        release once the minor version reaches double digits.
        """
        releases = []
        for tag in tags:
            match = RELEASE_TAG_PATTERN.match(tag)
            if match:
                major, minor, patch = match.groups()
                releases.append(((int(major), int(minor), int(patch or 0)), tag))

        if not releases:
            return FALLBACK_TAG
        return max(releases)[1]

    @staticmethod
    @activity.defn(name="ZsegmentFetchLatestTagActivity")
    async def defn() -> str:
        """
        Fetch the newest release tag published for zsegment-api.

        All modules are released at the same version, so one repository is
        enough to establish which release is current.
        """
        config: AppSettings = get_settings()
        url = f"{config.docker_registry.registry_url}/v2/zsegment-api/tags/list"
        try:
            response = httpx.get(
                url, auth=(config.docker_registry.registry_username, config.docker_registry.registry_password)
            )
            if response.is_success:
                tag = ZsegmentFetchLatestTagActivity.newest_release_tag(response.json().get("tags", []))
                log_info(f"Resolved zsegment release tag: {tag}")
                return tag
            response.raise_for_status()
        except Exception as e:
            log_error(f"Error fetching latest tag: {e=}")
        return FALLBACK_TAG


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
