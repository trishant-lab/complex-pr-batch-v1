from temporalio import activity, workflow
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import LaunchpadCLIBaseModel


with workflow.unsafe.imports_passed_through():
    from datetime import timedelta
    from app.cli.temporal.core.base import Activity
    from app.onepasswordutil import OnePasswordUtil


class OnePasswordCreateOrUpdateActivityModel(LaunchpadCLIBaseModel):
    """
    OnePasswordCreateOrUpdateActivityModel
    """

    tenant: str
    server_item: str
    vault: str
    secret_name: str
    secret_value: str


class OnePasswordCreateOrUpdateActivity(Activity):
    """
    OnePasswordCreateOrUpdateActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=60)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5, backoff_coefficient=2)

    @staticmethod
    @activity.defn(name="OnePasswordCreateOrUpdateActivity")
    async def defn(activity_input: OnePasswordCreateOrUpdateActivityModel) -> None:
        """
        Callable for the activity
        """
        OnePasswordUtil(
            tenant=activity_input.tenant,
            server_item=activity_input.server_item,
            vault=activity_input.vault,
        ).create_or_replace(activity_input.secret_name, activity_input.secret_value)


class OnePasswordGetActivityModel(LaunchpadCLIBaseModel):
    """
    OnePasswordGetActivityModel
    """

    tenant: str
    server_item: str
    vault: str
    secret_name: str


class OnePasswordGetActivity(Activity):
    """
    OnePasswordGetActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=60)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5, backoff_coefficient=2)

    @staticmethod
    @activity.defn(name="OnePasswordGetActivity")
    async def defn(activity_input: OnePasswordGetActivityModel) -> str | None:
        """
        Callable for the activity
        """
        return OnePasswordUtil(
            tenant=activity_input.tenant,
            server_item=activity_input.server_item,
            vault=activity_input.vault,
        ).get_key(key=activity_input.secret_name)
