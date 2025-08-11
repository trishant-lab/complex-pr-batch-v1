from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.one_password_util import OnePasswordUtil
from app.common import generate_password


class OnePasswordCreateOrUpdateActivityModel(LaunchpadCLIBaseModel):
    """
    OnePasswordCreateOrUpdateActivityModel
    """

    tenant: str
    server_item: str
    vault: str
    secret_name: str
    secret_value: str

class CreatePasswordActivity(Activity):
    """
    CreatePasswordActivity
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
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="CreatePasswordActivity")
    async def defn(length: int = 20) -> str:
        """
        Callable for the activity
        """
        return generate_password(length=length)

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
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="OnePasswordCreateOrUpdateActivity")
    async def defn(activity_input: OnePasswordCreateOrUpdateActivityModel) -> None:
        """
        Callable for the activity
        """
        await OnePasswordUtil(
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
        return RetryPolicy(initial_interval=timedelta(seconds=10), maximum_attempts=5, backoff_coefficient=3)

    @staticmethod
    @activity.defn(name="OnePasswordGetActivity")
    async def defn(activity_input: OnePasswordGetActivityModel) -> str | None:
        """
        Callable for the activity
        """
        return await OnePasswordUtil(
            tenant=activity_input.tenant,
            server_item=activity_input.server_item,
            vault=activity_input.vault,
        ).get_key(key=activity_input.secret_name)


class OnePasswordInsertIfNotExistsActivityModel(LaunchpadCLIBaseModel):
    """
    Model for inserting a fernet key if it doesn't exist
    """

    tenant: str
    vault: str
    server_item: str
    key: str
    key_value: str | None = None


class OnePasswordInsertIfNotExistsActivity(Activity):
    """
    Activity to insert key into 1Password if it doesn't exist
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
        return RetryPolicy(initial_interval=timedelta(seconds=10), maximum_attempts=5, backoff_coefficient=3)

    @staticmethod
    @activity.defn(name="OnePasswordInsertIfNotExistsActivity")
    async def defn(activity_input: OnePasswordInsertIfNotExistsActivityModel) -> None:
        """
        Callable for the activity that checks if a key exists for a tenant,
        and if not, generates and inserts a new one
        """
        server_item = activity_input.server_item
        op_util = OnePasswordUtil(
            tenant=activity_input.tenant,
            server_item=server_item,
            vault=activity_input.vault,
        )

        # Try to get existing key
        existing_key = await op_util.get_key(activity_input.key)

        if all([existing_key is None, activity_input.key_value is not None]):
            # Create or update the key
            await op_util.create_or_replace(activity_input.key, activity_input.key_value)
