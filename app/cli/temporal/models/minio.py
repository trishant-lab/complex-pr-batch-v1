from app.cli.temporal.core.base import LaunchpadCLIBaseModel


class CreateMinioBucketActivityModel(LaunchpadCLIBaseModel):
    """
    CreateMinioBucketActivityModel
    """

    bucket_name: str = ""
    region_name: str = ""


class AttachMinioPolicyActivityModel(LaunchpadCLIBaseModel):
    """
    AttachMinioPolicyActivityModel
    """

    bucket_name: str = ""
    access_key: str = ""


class CreateMinioUserActivityModel(LaunchpadCLIBaseModel):
    """
    CreateMinioUserActivityModel
    """

    access_key: str = ""
    secret_key: str = ""


class MinioBucketCredentials(LaunchpadCLIBaseModel):
    """
    MinioBucketCredentials
    """

    access_key: str | None = None
    secret_key: str | None = None
    exists: bool
