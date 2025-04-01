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
