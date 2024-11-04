from temporalio import activity, workflow
from temporalio.common import RetryPolicy


with workflow.unsafe.imports_passed_through():
    import zipfile
    import tempfile
    from datetime import timedelta
    from app.cli.temporal.core.base import Activity
    from app.cli.temporal.core.base import LaunchpadCLIBaseModel
    from app.cli.cloudflareUtils import (
        get_temporary_credentials,
        create_bucket,
        create_dns_record,
        link_bucket_to_custom_domain,
        delete_bucket,
        delete_dns_record,
    )
    from app.cli.temporal.core.log import log_error, log_info
    from app.core.settings import AppSettings, get_settings
    from app.s3_utils import download_file_from_storage, copy_files_to_cloudflare, get_storage_client


class CreateCloudflareBucketActivityModel(LaunchpadCLIBaseModel):
    """
    CreateCloudflareBucketActivityModel
    """

    bucket_name: str


class CreateCloudflareBucketActivity(Activity):
    """
    CreateCloudflareBucketActivity
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
    @activity.defn(name="CreateCloudflareBucketActivity")
    async def create_cloudflare_bucket(activity_input: CreateCloudflareBucketActivityModel) -> None:
        """
        Create a Cloudflare bucket
        """
        config: AppSettings = get_settings()

        bucket = await create_bucket(config=config, bucket_name=activity_input.bucket_name)

        log_info(f"Created bucket {bucket}")


class CreateCloudflareDNSRecordActivityModel(LaunchpadCLIBaseModel):
    """
    CreateCloudflareDNSRecordActivityModel
    """

    domain_name: str
    zone_id: str


class CreateCloudflareDNSRecordActivity(Activity):
    """
    CreateCloudflareDNSRecordActivity
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
    @activity.defn(name="CreateCloudflareDNSRecordActivity")
    async def create_cloudflare_dns_record(activity_input: CreateCloudflareDNSRecordActivityModel) -> None:
        """
        Create a Cloudflare DNS record
        """
        config: AppSettings = get_settings()

        dns_record = await create_dns_record(
            config=config, fqdn=activity_input.domain_name, zone_id=activity_input.zone_id
        )

        log_info(f"Created DNS record {dns_record}")


class LinkBucketToDomainActivityModel(LaunchpadCLIBaseModel):
    """
    LinkBucketToDomainActivityModel
    """

    bucket_name: str
    domain_name: str
    zone_id: str


class LinkBucketToDomainActivity(Activity):
    """
    LinkBucketToDomainActivity
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
    @activity.defn(name="LinkBucketToDomainActivity")
    async def link_bucket_to_domain(activity_input: LinkBucketToDomainActivityModel) -> None:
        """
        Link a bucket to a domain
        """
        config: AppSettings = get_settings()

        await link_bucket_to_custom_domain(
            config=config,
            bucket_name=activity_input.bucket_name,
            custom_domain=activity_input.domain_name,
            zone_id=activity_input.zone_id,
        )

        log_info(f"Linked bucket {activity_input.bucket_name} to domain {activity_input.domain_name}")


class CopyArtifactsToBucketActivityModel(LaunchpadCLIBaseModel):
    """
    CopyArtifactsToBucketActivityModel
    """

    bucket_name: str
    src_object_name: str
    bundle_name: str
    bundle_path: str
    dest_dir: str


class CopyArtifactsToBucketActivity(Activity):
    """
    CopyArtifactsToBucketActivity
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
    @activity.defn(name="CopyArtifactsToBucketActivity")
    async def copy_artifacts_to_bucket(activity_input: CopyArtifactsToBucketActivityModel) -> None:
        """
        Copy artifacts to a bucket
        """
        config: AppSettings = get_settings()

        environment: str = config.env

        artifacts_temporary_credentials = await get_temporary_credentials(config, "artifacts")
        artifacts_access_key = artifacts_temporary_credentials["accessKeyId"]
        artifacts_secret_key = artifacts_temporary_credentials["secretAccessKey"]

        artifacts_s3_client = get_storage_client(
            config=config,
            access_key=artifacts_access_key,
            secret_key=artifacts_secret_key,
            endpoint=config.cloudflare.endpoint,
        )

        bucket_temporary_credentials = await get_temporary_credentials(config, activity_input.bucket_name)
        bucket_access_key = bucket_temporary_credentials["accessKeyId"]
        bucket_secret_key = bucket_temporary_credentials["secretAccessKey"]

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                download_file_from_storage(
                    object_name=activity_input.src_object_name,
                    file_path=f"{tmp_dir}/{activity_input.bundle_name}",
                    storage_client=artifacts_s3_client,
                    bucket_name="artifacts",
                )

                # unzip the file
                with zipfile.ZipFile(f"{tmp_dir}/{activity_input.bundle_name}", "r") as zip_ref:
                    zip_ref.extractall(f"{tmp_dir}/bundle")

                # copy the files to the destination directory
                copy_files_to_cloudflare(
                    tenant=activity_input.tenant,
                    input_path=f"{tmp_dir}/{activity_input.bundle_path}",
                    output_path=activity_input.dest_dir,
                    endpoint=config.cloudflare.endpoint,
                    access_key=bucket_access_key,
                    secret_key=bucket_secret_key,
                )

                # todo: check if this is needed for all products
                if environment == "production":
                    copy_files_to_cloudflare(
                        tenant=activity_input.tenant,
                        input_path=f"{tmp_dir}/{activity_input.bundle_path}/index.html",
                        output_path=f"{activity_input.dest_dir}/custom/index.html",
                        endpoint=config.cloudflare.endpoint,
                        access_key=bucket_access_key,
                        secret_key=bucket_secret_key,
                    )

                log_info(f"UI setup completed for {activity_input.dest_dir}")

        except Exception as e:
            log_error(f"Error downloading UI bundle: {e}")
            raise e


class DeleteCloudflareBucketActivityModel(LaunchpadCLIBaseModel):
    """
    DeleteCloudflareBucketActivityModel
    """

    bucket_name: str


class DeleteCloudflareBucketActivity(Activity):
    """
    DeleteCloudflareBucketActivity
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
    @activity.defn(name="DeleteCloudflareBucketActivity")
    async def delete_cloudflare_bucket(activity_input: DeleteCloudflareBucketActivityModel) -> None:
        """
        Delete a Cloudflare bucket
        """
        config: AppSettings = get_settings()

        await delete_bucket(config=config, bucket_name=activity_input.bucket_name)


class DeleteCloudflareDNSRecordActivityModel(LaunchpadCLIBaseModel):
    """
    DeleteCloudflareDNSRecordActivityModel
    """

    domain_name: str
    zone_id: str


class DeleteCloudflareDNSRecordActivity(Activity):
    """
    DeleteCloudflareDNSRecordActivity
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
    @activity.defn(name="DeleteCloudflareDNSRecordActivity")
    async def delete_cloudflare_dns_record(activity_input: DeleteCloudflareDNSRecordActivityModel) -> None:
        """
        Delete a Cloudflare DNS record
        """
        config: AppSettings = get_settings()

        await delete_dns_record(config=config, fqdn=activity_input.domain_name, zone_id=activity_input.zone_id)
