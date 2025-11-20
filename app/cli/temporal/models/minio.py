from app.cli.temporal.core.base import LaunchpadCLIBaseModel
from app.core.settings import S3Settings


class CreateMinioBucketActivityModel(LaunchpadCLIBaseModel):
    """
    CreateMinioBucketActivityModel
    """

    bucket_name: str = ""
    region_name: str = ""
    s3_config: S3Settings | None = None


class AttachMinioPolicyActivityModel(LaunchpadCLIBaseModel):
    """
    AttachMinioPolicyActivityModel
    """

    bucket_name: str = ""
    access_key: str = ""
    s3_config: S3Settings | None = None


class CreateMinioUserActivityModel(LaunchpadCLIBaseModel):
    """
    CreateMinioUserActivityModel
    """

    access_key: str = ""
    secret_key: str = ""
    s3_config: S3Settings | None = None


class MinioBucketCredentials(LaunchpadCLIBaseModel):
    """
    MinioBucketCredentials
    """

    access_key: str | None = None
    secret_key: str | None = None
    exists: bool
    s3_config: S3Settings | None = None
