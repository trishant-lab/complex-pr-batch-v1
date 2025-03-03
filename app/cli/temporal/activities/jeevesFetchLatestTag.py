import subprocess
import tempfile
from datetime import timedelta

from loguru import logger
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_error
from app.core.settings import AppSettings, get_settings


class JeevesFetchLatestTagActivityModel(LaunchpadCLIBaseModel):
    """
    JeevesFetchLatestTagActivityModel
    """

    repo_url: str


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
    async def defn(activity_input: JeevesFetchLatestTagActivityModel) -> str:
        """
        Fetch latest tags
        """
        config: AppSettings = get_settings()
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                subprocess.check_call(
                    ["git", "clone", activity_input.repo_url.format(config.gitsettings.access_token), tmp_dir],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                subprocess.check_call(["git", "fetch", "--tags"], cwd=tmp_dir)
                tags = subprocess.check_output(["git", "tag"], cwd=tmp_dir, text=True).strip()
                if not tags:
                    return ""
                subprocess.check_call(["git", "checkout", "production"], cwd=tmp_dir)
                tag = subprocess.check_output(
                    ["git", "describe", "--tags", "--abbrev=0"], cwd=tmp_dir, text=True
                ).strip()
                # TODO: removeb this tag once verified
                logger.debug(f"Latest tag : {tag=}")
                return tag
            except subprocess.CalledProcessError as e:
                log_error(f"Failed to fetch latest tag with exception: {e=}")
                return "production"
