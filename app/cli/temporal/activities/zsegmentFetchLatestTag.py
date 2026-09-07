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
