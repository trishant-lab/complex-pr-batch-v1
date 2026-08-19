from enum import StrEnum

from app.cli.temporal.core.base import LaunchpadCLIBaseModel


class QueueConsumerType(StrEnum):
    """
    Consumer types supported by a Cloudflare queue. A queue can have only one consumer.
    """

    # Push-based: Cloudflare invokes a Worker's queue() handler with batches of messages.
    WORKER = "worker"
    # Pull-based: the consumer polls the queue for a batch and acknowledges the messages itself.
    HTTP_PULL = "http_pull"


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


class WorkersKVConfigUploadActivityModel(LaunchpadCLIBaseModel):
    """
    WorkersKVConfigUploadActivityModel

    Fetches the template from `cloudflare_r2_folder_path` in the launchpad-config-templates
    bucket on R2, renders Jinja with `template_payload`, injects 1Password secrets
    (`{{op://...}}` refs), and uploads the result to the named Workers KV namespace under `key`.
    """

    namespace_id: str
    key: str
    template_file_name: str
    template_payload: dict
    cloudflare_r2_folder_path: str


class AddBucketsToR2TokenActivityModel(LaunchpadCLIBaseModel):
    """
    AddBucketsToR2TokenActivityModel

    Set `read_only=True` to extend the token's read-permission-group policy instead of
    the write one — used to grant a shared reader token access to a new tenant bucket.
    """

    token_name: str
    bucket_names: list[str]
    read_only: bool = False


class CreateCloudflareQueueActivityModel(LaunchpadCLIBaseModel):
    """
    CreateCloudflareQueueActivityModel
    """

    queue_name: str
    # When None the queue keeps Cloudflare's default retention.
    message_retention_period: int | None = None
    consumer_type: QueueConsumerType = QueueConsumerType.HTTP_PULL


class DeleteCloudflareQueueActivityModel(LaunchpadCLIBaseModel):
    """
    DeleteCloudflareQueueActivityModel
    """

    queue_names: list[str]


class WorkersKVDeleteKeysActivityModel(LaunchpadCLIBaseModel):
    """
    WorkersKVDeleteKeysActivityModel

    Deletes `keys` from the Cloudflare Workers KV namespace.
    """

    namespace_id: str
    keys: list[str]


class WorkersKVPutActivityModel(LaunchpadCLIBaseModel):
    """
    WorkersKVPutActivityModel

    Writes `value` (JSON-serialized) to the Cloudflare Workers KV namespace under `key`.
    """

    namespace_id: str
    key: str
    value: dict
