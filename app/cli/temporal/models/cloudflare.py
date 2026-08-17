from app.cli.temporal.core.base import LaunchpadCLIBaseModel


class CreateCloudflareBucketCredentialsActivityModel(LaunchpadCLIBaseModel):
    """
    CreateCloudflareBucketCredentialsActivityModel
    """

    bucket_name: str
    read_only: bool = False


class CloudflareBucketCredentials(LaunchpadCLIBaseModel):
    """
    CloudflareBucketCredentials
    """

    access_key: str | None = None
    secret_key: str | None = None
    exists: bool


class CreateCloudflareBucketActivityModel(LaunchpadCLIBaseModel):
    """
    CreateCloudflareBucketActivityModel
    """

    bucket_name: str
    location_hint: str | None = None  # Possible values: ["apac", "eeur", "enam", "weur", "wnam"]


class CreateCloudflareDNSRecordActivityModel(LaunchpadCLIBaseModel):
    """
    CreateCloudflareDNSRecordActivityModel
    """

    domain_name: str
    zone_id: str
    content: str | None = None


class LinkBucketToDomainActivityModel(LaunchpadCLIBaseModel):
    """
    LinkBucketToDomainActivityModel
    """

    bucket_name: str
    domain_name: str
    zone_id: str


class CopyArtifactsToBucketActivityModel(LaunchpadCLIBaseModel):
    """
    CopyArtifactsToBucketActivityModel
    """

    tenant: str
    bucket_name: str
    src_object_name: str
    bundle_name: str
    bundle_path: str
    dest_dir: str


class CopyWebCoreToBucketActivityModel(LaunchpadCLIBaseModel):
    """
    CopyWebCoreToBucketActivityModel
    """

    src_object_name: str
    tenant: str
    bucket_name: str
    bundle_name: str
    dest_dir: str


class DeleteCloudflareBucketActivityModel(LaunchpadCLIBaseModel):
    """
    DeleteCloudflareBucketActivityModel
    """

    bucket_name: str


class DeleteFilesFromCloudflareActivityModel(LaunchpadCLIBaseModel):
    """
    DeleteFilesFromCloudflareActivityModel
    """

    tenant: str
    bucket_name: str


class DeleteCloudflareDNSRecordActivityModel(LaunchpadCLIBaseModel):
    """
    DeleteCloudflareDNSRecordActivityModel
    """

    domain_name: str
    zone_id: str


class PropagateDNSRecordActivityModel(LaunchpadCLIBaseModel):
    """
    PropagateDNSRecordActivityModel
    """

    domain_name: str


class PenknifeCopyArtifactsToBucketActivityModel(LaunchpadCLIBaseModel):
    """
    PenknifeCopyArtifactsToBucketActivityModel
    """

    tenant: str
    bucket_name: str
    careerportal_bucket_name: str
    src_object_name: str
    bundle_name: str


class UpdateCORSForBucketActivityModel(LaunchpadCLIBaseModel):
    """
    UpdateCORSForBucketActivityModel
    """

    bucket_name: str
    rules: list[dict]


class AddBucketsToR2TokenActivityModel(LaunchpadCLIBaseModel):
    """
    AddBucketsToR2TokenActivityModel

    Set `read_only=True` to extend the token's read-permission-group policy instead of
    the write one — used to grant a shared reader token access to a new tenant bucket.
    """

    token_name: str
    bucket_names: list[str]
    read_only: bool = False
