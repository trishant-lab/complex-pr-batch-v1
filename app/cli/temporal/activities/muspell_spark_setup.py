from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.core.product_settings.muspell_archive import MuspellArchiveSettings


class MuspellSparkSetupActivityModel(LaunchpadCLIBaseModel):
    """
    MuspellSparkSetupActivityModel
    """

    muspell_config: MuspellArchiveSettings
    container_name: str
    container_hostname: str


class MuspellSparkSetupActivity(Activity):
    """
    MuspellSparkSetupActivity
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
        RetryPolicy for the activity
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="MuspellSparkSetupActivity")
    async def defn(activity_model: MuspellSparkSetupActivityModel) -> None:
        """
        MuspellSparkSetupActivity
        """
        _volumes = {
            f"/data/mounts/{activity_model.container_name}/spark-defaults.conf": {
                "bind": "/opt/spark/conf/spark-defaults.conf",
                "mode": "rw",
            },
            f"/data/mounts/{activity_model.container_name}/work-dir": {"bind": "/opt/spark/work-dir", "mode": "rw"},
        }
