from datetime import timedelta
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity
from app.cli.temporal.models.minio import (
    AttachMinioPolicyActivityModel,
    CreateMinioBucketActivityModel,
    CreateMinioUserActivityModel,
    MinioBucketCredentials,
)
from app.core.settings import AppSettings, S3Settings, get_settings


class CreateMinioBucketActivity(Activity):
    """
    CreateMinioBucketActivity
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
    @activity.defn(name="CreateMinioBucketActivity")
    async def defn(activity_input: CreateMinioBucketActivityModel) -> None:
        """
        Create a Minio bucket
        """
        config: AppSettings = get_settings()

        from app.s3_utils import create_minio_bucket

        s3_config: S3Settings = activity_input.s3_config if activity_input.s3_config is not None else config.s3_int

        await create_minio_bucket(
            s3_config=s3_config,
            bucket_name=activity_input.bucket_name,
            region_name=activity_input.region_name,
        )


class AttachMinioPolicyActivity(Activity):
    """
    AttachMinioPolicyActivity
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
    @activity.defn(name="AttachMinioPolicyActivity")
    async def defn(activity_input: AttachMinioPolicyActivityModel) -> None:
        """
        Attach a Minio policy to a user
        """
        from app.s3_utils import attach_minio_policy

        config: AppSettings = get_settings()

        s3_config: S3Settings = activity_input.s3_config if activity_input.s3_config is not None else config.s3_int

        await attach_minio_policy(
            s3_config=s3_config,
            bucket_name=activity_input.bucket_name,
            access_key=activity_input.access_key,
        )


class CreateMinioUserActivity(Activity):
    """
    CreateMinioUserActivity
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
    @activity.defn(name="CreateMinioUserActivity")
    async def defn(activity_input: CreateMinioUserActivityModel) -> MinioBucketCredentials:
        """
        Create Minio user
        """
        from app.s3_utils import create_minio_user

        config: AppSettings = get_settings()

        s3_config: S3Settings = activity_input.s3_config if activity_input.s3_config is not None else config.s3_int

        return await create_minio_user(
            s3_config=s3_config,
            access_key=activity_input.access_key,
            secret_key=activity_input.secret_key,
        )
