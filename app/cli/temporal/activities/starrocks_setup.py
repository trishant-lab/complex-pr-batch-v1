from datetime import timedelta
from app.cli.temporal.core.base import Activity
from app.cli.temporal.models.starrocks import CreateStarRocksCatalogActivityModel
from app.core.settings import AppSettings, get_settings
from temporalio import activity
from temporalio.common import RetryPolicy

from app.starrocks_utils import (
    CreateStarRocksInputModel,
    GrantStarRocksReadOnlyCatalogModel,
    RegisterStarrocksUserModel,
)


class CreateStarRocksCatalogActivity(Activity):
    """
    CreateStarRocksCatalogActivity
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
        return RetryPolicy(initial_interval=timedelta(seconds=10), maximum_attempts=5, backoff_coefficient=3)

    @staticmethod
    @activity.defn(name="CreateStarRocksCatalogActivity")
    async def defn(activity_input: CreateStarRocksCatalogActivityModel) -> None:
        """
        CreateStarRocksCatalogActivity
        """
        config: AppSettings = get_settings()

        from app.starrocks_utils import create_starrocks_catalog

        starrocks_input = CreateStarRocksInputModel(
            muspell_config=config.muspell,
            tenant=activity_input.tenant,
            warehouse_access_key=activity_input.warehouse_access_key,
            warehouse_secret_key=activity_input.warehouse_secret_key,
            catalog_name=activity_input.catalog_name,
        )

        await create_starrocks_catalog(starrocks_input)


class CreateStarRocksUserActivity(Activity):
    """
    CreateStarRocksUserActivity
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
        return RetryPolicy(initial_interval=timedelta(seconds=10), maximum_attempts=5, backoff_coefficient=3)

    @staticmethod
    @activity.defn(name="CreateStarRocksUserActivity")
    async def defn(activity_input: RegisterStarrocksUserModel) -> None:
        """
        CreateStarRocksUserActivity
        """
        from app.starrocks_utils import register_user

        await register_user(activity_input)


class StarRocksGrantReadOnlyCatalogActivity(Activity):
    """
    StarRocksGrantReadOnlyCatalogActivity - grants read-only access on the catalog to a
    pre-existing StarRocks user. Silently no-ops if the user does not exist.
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
        return RetryPolicy(initial_interval=timedelta(seconds=10), maximum_attempts=5, backoff_coefficient=3)

    @staticmethod
    @activity.defn(name="StarRocksGrantReadOnlyCatalogActivity")
    async def defn(activity_input: GrantStarRocksReadOnlyCatalogModel) -> None:
        """
        Grant read-only access on the catalog to a pre-existing user.
        """
        from app.starrocks_utils import grant_read_only_to_catalog

        await grant_read_only_to_catalog(activity_input)
