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
    MuspellConfigUpdateJobActivityModel
    """

    column_config: dict
    organization_config: dict
    schema_name: str
    database_name: str
    username: str
    password: str


class MuspellConfigUpdateJobActivity(Activity):
    """
    MuspellConfigUpdateJobActivity
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
    @activity.defn(name="MuspellConfigUpdateJobActivity")
    async def defn(activity_model: MuspellConfigUpdateJobActivityModel) -> None:
        """
        MuspellConfigUpdateJobActivity
        """
        config: AppSettings = get_settings()

        pg_dsn = MultiHostUrl(
            f"postgres://{activity_model.username}:{activity_model.password}@{config.postgres.host}:{config.postgres.port}/{activity_model.database_name}"
        )
        db_manager = await get_db_manager(pg_dsn)

        await db_manager.execute(
            sqlfile="muspell/update_config.sql",
            db_schema_name=activity_model.schema_name,
            config_value=activity_model.column_config,
            config_type="column",
        )
        log_info(f"Updated column config for {activity_model.schema_name} successfully.")

        await db_manager.execute(
            sqlfile="muspell/update_config.sql",
            db_schema_name=activity_model.schema_name,
            config_value=activity_model.organization_config,
            config_type="organization",
        )
        log_info(f"Updated organization config for {activity_model.schema_name} successfully.")
