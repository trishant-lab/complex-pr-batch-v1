import asyncio
import socket
from temporalio import activity
from temporalio.common import RetryPolicy


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
from app.s3_utils import (
    download_file_from_storage,
    mirror_files_to_cloudflare,
    get_storage_client,
    delete_files_from_cloudflare,
    copy_files_to_cloudflare,
    copy_files_to_cloudflare_with_exclude,
)


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
    async def defn(activity_input: CreateCloudflareBucketActivityModel) -> None:
        """
        Create a Cloudflare bucket
        """
        config: AppSettings = get_settings()

        await create_bucket(config=config, bucket_name=activity_input.bucket_name)

        log_info(f"Created bucket {activity_input.bucket_name}")


class CreateCloudflareDNSRecordActivityModel(LaunchpadCLIBaseModel):
    """
    CreateCloudflareDNSRecordActivityModel
    """

    domain_name: str
    zone_id: str
    content: str | None = None


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
    async def defn(activity_input: CreateCloudflareDNSRecordActivityModel) -> None:
        """
        Create a Cloudflare DNS record
        """
        config: AppSettings = get_settings()
        await create_dns_record(
            config=config,
            fqdn=activity_input.domain_name,
            zone_id=activity_input.zone_id,
            content=activity_input.content,
        )


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
    async def defn(activity_input: LinkBucketToDomainActivityModel) -> None:
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

    tenant: str
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
    async def defn(activity_input: CopyArtifactsToBucketActivityModel) -> None:
        """
        Copy artifacts to a bucket
        """
        config: AppSettings = get_settings()

        environment: str = config.env

        # artifacts_temporary_credentials = await get_temporary_credentials(config, "artifacts")
        artifacts_access_key = config.cloudflare.r2_access_key
        artifacts_secret_key = config.cloudflare.r2_secret_key

        artifacts_s3_client = get_storage_client(
            config=config,
            access_key=artifacts_access_key,
            secret_key=artifacts_secret_key,
            endpoint=config.cloudflare.r2_endpoint,
        )

        bucket_temporary_credentials = await get_temporary_credentials(config, activity_input.bucket_name)
        bucket_access_key = bucket_temporary_credentials.access_key_id
        bucket_secret_key = bucket_temporary_credentials.secret_access_key
        bucket_session_token = bucket_temporary_credentials.session_token

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
                mirror_files_to_cloudflare(
                    tenant=activity_input.tenant,
                    input_path=f"{tmp_dir}/{activity_input.bundle_path}",
                    output_path=activity_input.dest_dir,
                    endpoint=config.cloudflare.r2_endpoint,
                    access_key=bucket_access_key,
                    secret_key=bucket_secret_key,
                    session_token=bucket_temporary_credentials.session_token,
                )

                # todo: check if this is needed for all products
                if environment == "production":
                    mirror_files_to_cloudflare(
                        tenant=activity_input.tenant,
                        input_path=f"{tmp_dir}/{activity_input.bundle_path}/index.html",
                        output_path=f"{activity_input.dest_dir}/custom/index.html",
                        endpoint=config.cloudflare.r2_endpoint,
                        access_key=bucket_access_key,
                        secret_key=bucket_secret_key,
                        session_token=bucket_session_token,
                    )

                log_info(f"UI setup completed for {activity_input.dest_dir}")

        except Exception as e:
            log_error(f"Error downloading UI bundle: {e}")
            raise e


class CopyWebCoreToBucketActivityModel(LaunchpadCLIBaseModel):
    """
    CopyWebCoreToBucketActivityModel
    """

    src_object_name: str
    tenant: str
    bucket_name: str
    bundle_name: str
    dest_dir: str


class CopyWebCoreToBucketActivity(Activity):
    """
    CopyWebCoreToBucketActivity
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
    @activity.defn(name="CopyWebCoreToBucketActivity")
    async def defn(activity_input: CopyWebCoreToBucketActivityModel) -> None:
        """
        Copy webcore to a bucket
        """
        config: AppSettings = get_settings()

        bucket_temporary_credentials = await get_temporary_credentials(config, activity_input.bucket_name)
        bucket_access_key = bucket_temporary_credentials.access_key_id
        bucket_secret_key = bucket_temporary_credentials.secret_access_key

        artifacts_access_key = config.cloudflare.r2_access_key
        artifacts_secret_key = config.cloudflare.r2_secret_key
        artifacts_s3_client = get_storage_client(
            config=config,
            access_key=artifacts_access_key,
            secret_key=artifacts_secret_key,
            endpoint=config.cloudflare.r2_endpoint,
        )
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                download_file_from_storage(
                    object_name=activity_input.src_object_name,
                    file_path=f"{tmp_dir}/{activity_input.bundle_name}",
                    storage_client=artifacts_s3_client,
                    bucket_name="artifacts",
                )

                copy_files_to_cloudflare(
                    tenant=activity_input.tenant,
                    input_path=f"{tmp_dir}/{activity_input.bundle_name}",
                    output_path=activity_input.dest_dir,
                    endpoint=config.cloudflare.r2_endpoint,
                    access_key=bucket_access_key,
                    secret_key=bucket_secret_key,
                    session_token=bucket_temporary_credentials.session_token,
                )

                log_info(f"Web Core Deployment successful: {activity_input.tenant}")

        except Exception as e:
            log_error(f"Error deploying webcore: {e}")
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
    async def defn(activity_input: DeleteCloudflareBucketActivityModel) -> None:
        """
        Delete a Cloudflare bucket
        """
        config: AppSettings = get_settings()

        try:
            await delete_bucket(config=config, bucket_name=activity_input.bucket_name)
        except Exception as e:
            log_error(f"Error deleting bucket {activity_input.bucket_name}: {e}")


class DeleteFilesFromCloudflareActivityModel(LaunchpadCLIBaseModel):
    """
    DeleteFilesFromCloudflareActivityModel
    """

    tenant: str
    bucket_name: str


class DeleteFilesFromCloudflareActivity(Activity):
    """
    DeleteFilesFromCloudflareActivity
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
    @activity.defn(name="DeleteFilesFromCloudflareActivity")
    async def defn(activity_input: DeleteFilesFromCloudflareActivityModel) -> None:
        """
        Delete files from Cloudflare
        """
        config: AppSettings = get_settings()
        bucket_temporary_credentials = await get_temporary_credentials(config, activity_input.bucket_name)
        bucket_access_key = bucket_temporary_credentials.access_key_id
        bucket_secret_key = bucket_temporary_credentials.secret_access_key

        try:
            delete_files_from_cloudflare(
                tenant=activity_input.tenant,
                input_path=f"{activity_input.bucket_name}/",
                endpoint=config.cloudflare.r2_endpoint,
                access_key=bucket_access_key,
                secret_key=bucket_secret_key,
                session_token=bucket_temporary_credentials.session_token,
            )
        except Exception as e:
            log_error(f"Error deleting files from Cloudflare: {e}")


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
    async def defn(activity_input: DeleteCloudflareDNSRecordActivityModel) -> None:
        """
        Delete a Cloudflare DNS record
        """
        config: AppSettings = get_settings()

        try:
            await delete_dns_record(config=config, fqdn=activity_input.domain_name, zone_id=activity_input.zone_id)
        except Exception as e:
            log_error(f"Error deleting DNS record {activity_input.domain_name}: {e}")


class PropagateDNSRecordActivityModel(LaunchpadCLIBaseModel):
    """
    PropagateDNSRecordActivityModel
    """

    domain_name: str


class PropagateDNSRecordActivity(Activity):
    """
    PropagateDNSRecordActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=600)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5, backoff_coefficient=2)

    @staticmethod
    @activity.defn(name="PropagateDNSRecordActivity")
    async def defn(activity_input: PropagateDNSRecordActivityModel) -> None:
        """
        Propagate a DNS record
        """
        count = 0
        while True:
            try:
                socket.getaddrinfo(activity_input.domain_name, 0)
                break
            except socket.gaierror:
                count += 1
                if count == 61:
                    raise Exception(f"DNS propagation check timed out after [10 min]: {activity_input.domain_name}")
                log_info(f"DNS not propagated yet: {activity_input.domain_name}")
                await asyncio.sleep(10)


class PenknifeCopyArtifactsToBucketActivityModel(LaunchpadCLIBaseModel):
    """
    PenknifeCopyArtifactsToBucketActivityModel
    """

    tenant: str
    bucket_name: str
    careerportal_bucket_name: str
    src_object_name: str
    bundle_name: str


class PenknifeCopyArtifactsToBucketActivity(Activity):
    """
    PenknifeCopyArtifactsToBucketActivity
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
    @activity.defn(name="PenknifeCopyArtifactsToBucketActivity")
    async def defn(activity_input: PenknifeCopyArtifactsToBucketActivityModel) -> None:
        """
        Copy artifacts to a bucket
        """
        config: AppSettings = get_settings()

        environment: str = config.env

        artifacts_access_key = config.cloudflare.r2_access_key
        artifacts_secret_key = config.cloudflare.r2_secret_key

        artifacts_s3_client = get_storage_client(
            config=config,
            access_key=artifacts_access_key,
            secret_key=artifacts_secret_key,
            endpoint=config.cloudflare.r2_endpoint,
        )

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

                # copy artifacts for main UI

                bucket_temporary_credentials = await get_temporary_credentials(config, activity_input.bucket_name)
                bucket_access_key = bucket_temporary_credentials.access_key_id
                bucket_secret_key = bucket_temporary_credentials.secret_access_key

                image_tag = "production" if environment == "production" else "sprint"

                if environment == "production":
                    dest_dir = f"{activity_input.bucket_name}/"
                else:
                    dest_dir = f"{activity_input.bucket_name}/{image_tag}"

                copy_files_to_cloudflare_with_exclude(
                    tenant=activity_input.tenant,
                    input_path=f"{tmp_dir}/bundle/dist",
                    output_path=dest_dir,
                    exclude_pattern="dist/careerpages/**",
                    endpoint=config.cloudflare.r2_endpoint,
                    access_key=bucket_access_key,
                    secret_key=bucket_secret_key,
                    session_token=bucket_temporary_credentials.session_token,
                )

                # copy artifacts for careerportal UI

                bucket_temporary_credentials = await get_temporary_credentials(
                    config, activity_input.careerportal_bucket_name
                )
                bucket_access_key = bucket_temporary_credentials.access_key_id
                bucket_secret_key = bucket_temporary_credentials.secret_access_key

                # copy "apply" directory
                mirror_files_to_cloudflare(
                    tenant=activity_input.tenant,
                    input_path=f"{tmp_dir}/bundle/dist/careerpages/apply",
                    output_path=f"{activity_input.careerportal_bucket_name}/apply",
                    endpoint=config.cloudflare.r2_endpoint,
                    access_key=bucket_access_key,
                    secret_key=bucket_secret_key,
                    session_token=bucket_temporary_credentials.session_token,
                )

                # copy "public" directory
                mirror_files_to_cloudflare(
                    tenant=activity_input.tenant,
                    input_path=f"{tmp_dir}/bundle/dist/careerpages/public",
                    output_path=f"{activity_input.careerportal_bucket_name}/public",
                    endpoint=config.cloudflare.r2_endpoint,
                    access_key=bucket_access_key,
                    secret_key=bucket_secret_key,
                    session_token=bucket_temporary_credentials.session_token,
                )

                # todo: check artifact copy for production, since we are using tag based copy from artifact

                log_info(f"UI setup completed for {activity_input.tenant}")

        except Exception as e:
            log_error(f"Error downloading UI bundle: {e}")
            raise e
