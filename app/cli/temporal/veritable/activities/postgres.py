from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity
from app.cli.veritable.models.VeritableSpec import VeritableSpec


class PostgresDatabaseSetupActivity(Activity):
    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="PostgresDatabaseSetupActivity")
    async def defn(veritable: VeritableSpec) -> None:
        """
        Callable for the activity
        """
        from loguru import logger
        from app.cli.veritable.postgresSetup import setup_postgres

        logger.info(f"Setting up Postgres for tenant: {veritable.tenant}")
        await setup_postgres(veritable=veritable)
