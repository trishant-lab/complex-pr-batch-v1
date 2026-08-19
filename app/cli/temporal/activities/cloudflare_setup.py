import asyncio
import json
import os
import socket
import zipfile
from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity
from app.cli.temporal.core.log import log_error, log_info
from app.cli.temporal.models.cloudflare import (
    AddBucketsToR2TokenActivityModel,
    CloudflareBucketCredentials,
    CopyArtifactsToBucketActivityModel,
    CopyWebCoreToBucketActivityModel,
    CreateCloudflareBucketActivityModel,
    CreateCloudflareBucketCredentialsActivityModel,
    CreateCloudflareDNSRecordActivityModel,
    CreateCloudflareQueueActivityModel,
    DeleteCloudflareBucketActivityModel,
    DeleteCloudflareDNSRecordActivityModel,
    DeleteCloudflareQueueActivityModel,
    DeleteFilesFromCloudflareActivityModel,
    LinkBucketToDomainActivityModel,
    PenknifeCopyArtifactsToBucketActivityModel,
    PropagateDNSRecordActivityModel,
    UpdateCORSForBucketActivityModel,
    WorkersKVConfigUploadActivityModel,
    WorkersKVDeleteKeysActivityModel,
    WorkersKVPutActivityModel,
)
from app.core.settings import AppSettings, get_settings
from app.s3_utils import (
    copy_files_to_cloudflare,
    copy_files_to_cloudflare_with_exclude,
    delete_files_from_cloudflare,
    download_file_from_storage,
    sync_and_verify_files,
)
from app.one_password_util import secret_inject_drop_empty
from app.template_env import get_env
from app.utils.file_operations import get_opendal_file_client
from app.utils.s3_operations import get_s3_client


class CreateCloudflareBucketActivity(Activity):
    """
    CreateCloudflareBucketActivity
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
    @activity.defn(name="CreateCloudflareBucketActivity")
    async def defn(activity_input: CreateCloudflareBucketActivityModel) -> None:
        """
        Create a Cloudflare bucket
        """
        from app.cli.cloudflare_utils import create_bucket

        config: AppSettings = get_settings()

        await create_bucket(
            config=config,
            bucket_name=activity_input.bucket_name,
            location_hint=activity_input.location_hint,
        )

        log_info(f"Created bucket {activity_input.bucket_name}")


class CreateCloudflareQueueActivity(Activity):
    """
    CreateCloudflareQueueActivity
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
    @activity.defn(name="CreateCloudflareQueueActivity")
    async def defn(activity_input: CreateCloudflareQueueActivityModel) -> str:
        """
        Create a Cloudflare queue and attach a consumer of the requested type to it (all
        idempotent), then return the queue id. The message retention period is only applied
        when one is supplied, otherwise the queue keeps Cloudflare's default.
        """
        from app.cli.cloudflare_utils import create_queue, create_queue_consumer, set_queue_message_retention

        config: AppSettings = get_settings()

        queue_id = await create_queue(
            config=config,
            queue_name=activity_input.queue_name,
        )
        if not queue_id:
            # Never hand a falsy id back to the workflow -- downstream steps would persist it as null.
            raise RuntimeError(f"Cloudflare returned no queue id for {activity_input.queue_name}")

        log_info(f"Created queue {activity_input.queue_name} with id {queue_id}")

        if activity_input.message_retention_period:
            await set_queue_message_retention(
                config=config,
                queue_id=queue_id,
                message_retention_period=activity_input.message_retention_period,
            )

        consumer_id = await create_queue_consumer(
            config=config,
            queue_id=queue_id,
            consumer_type=activity_input.consumer_type,
        )

        log_info(f"Attached {activity_input.consumer_type} consumer {consumer_id} to queue {activity_input.queue_name}")
        return queue_id


class DeleteCloudflareQueueActivity(Activity):
    """
    DeleteCloudflareQueueActivity
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
    @activity.defn(name="DeleteCloudflareQueueActivity")
    async def defn(activity_input: DeleteCloudflareQueueActivityModel) -> None:
        """
        Delete the given Cloudflare queues (idempotent).
        """
        from app.cli.cloudflare_utils import delete_queue, get_queues

        config: AppSettings = get_settings()

        # queues that no longer exist are left out, so only the ones that resolved are deleted
        queues = await get_queues(config=config, queue_names=activity_input.queue_names)

        for queue in queues:
            await delete_queue(config=config, queue_id=queue.queue_id)
            log_info(f"Deleted queue {queue.queue_id}")


class WorkersKVDeleteKeysActivity(Activity):
    """
    WorkersKVDeleteKeysActivity
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
    @activity.defn(name="WorkersKVDeleteKeysActivity")
    async def defn(activity_input: WorkersKVDeleteKeysActivityModel) -> None:
        """
        Delete the given keys from a Cloudflare Workers KV namespace.
        """
        from app.cli.cloudflare_utils import workers_kv_delete_key

        config: AppSettings = get_settings()

        for key in activity_input.keys:
            await workers_kv_delete_key(
                config=config,
                namespace_id=activity_input.namespace_id,
                key=key,
            )
            log_info(f"Deleted KV key {key} from namespace {activity_input.namespace_id}")


class WorkersKVPutActivity(Activity):
    """
    WorkersKVPutActivity
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
    @activity.defn(name="WorkersKVPutActivity")
    async def defn(activity_input: WorkersKVPutActivityModel) -> None:
        """
        Write a JSON value to a Cloudflare Workers KV namespace under `key`.
        """
        from app.cli.cloudflare_utils import workers_kv_config_upload

        config: AppSettings = get_settings()

        await workers_kv_config_upload(
            config=config,
            namespace_id=activity_input.namespace_id,
            key=activity_input.key,
            value=json.dumps(activity_input.value),
        )

        log_info(f"Wrote KV key {activity_input.key} to namespace {activity_input.namespace_id}")


class CreateCloudflareDNSRecordActivity(Activity):
    """
    CreateCloudflareDNSRecordActivity
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
    @activity.defn(name="CreateCloudflareDNSRecordActivity")
    async def defn(activity_input: CreateCloudflareDNSRecordActivityModel) -> None:
        """
        Create a Cloudflare DNS record
        """
        from app.cli.cloudflare_utils import create_dns_record

        config: AppSettings = get_settings()
        await create_dns_record(
            config=config,
            fqdn=activity_input.domain_name,
            zone_id=activity_input.zone_id,
            content=activity_input.content,
        )


class LinkBucketToDomainActivity(Activity):
    """
    LinkBucketToDomainActivity
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
    @activity.defn(name="LinkBucketToDomainActivity")
    async def defn(activity_input: LinkBucketToDomainActivityModel) -> None:
        """
        Link a bucket to a domain
        """
        from app.cli.cloudflare_utils import link_bucket_to_custom_domain

        config: AppSettings = get_settings()

        await link_bucket_to_custom_domain(
            config=config,
            bucket_name=activity_input.bucket_name,
            custom_domain=activity_input.domain_name,
            zone_id=activity_input.zone_id,
        )

        log_info(f"Linked bucket {activity_input.bucket_name} to domain {activity_input.domain_name}")


class CopyArtifactsToBucketActivity(Activity):
    """
    CopyArtifactsToBucketActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(minutes=20)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), maximum_attempts=5, backoff_coefficient=3)

    @staticmethod
    @activity.defn(name="CopyArtifactsToBucketActivity")
    async def defn(activity_input: CopyArtifactsToBucketActivityModel) -> None:
        """
        Copy artifacts to a bucket
        """
        from app.cli.cloudflare_utils import get_temporary_credentials

        config: AppSettings = get_settings()

        artifacts_access_key = config.cloudflare.r2_access_key
        artifacts_secret_key = config.cloudflare.r2_secret_key

        artifacts_s3_client = get_s3_client(
            access_key=artifacts_access_key,
            secret_key=artifacts_secret_key,
            endpoint=config.cloudflare.r2_endpoint,
            bucket_name="artifacts",
        )

        bucket_temporary_credentials = await get_temporary_credentials(config, activity_input.bucket_name)
        bucket_access_key = bucket_temporary_credentials.access_key_id
        bucket_secret_key = bucket_temporary_credentials.secret_access_key
        bucket_session_token = bucket_temporary_credentials.session_token

        try:
            opendal_file_operations = get_opendal_file_client()
            async with opendal_file_operations.temp_dir() as tmp_dir:
                temp_file_path = os.path.join(opendal_file_operations.tempdir_root, tmp_dir, activity_input.bundle_name)

                await download_file_from_storage(
                    object_name=activity_input.src_object_name,
                    file_path=temp_file_path,
                    storage_client=artifacts_s3_client,
                )

                # unzip the file
                with zipfile.ZipFile(temp_file_path, "r") as zip_ref:
                    zip_ref.extractall(os.path.join(opendal_file_operations.tempdir_root, tmp_dir, "bundle"))

                storage_client = get_s3_client(
                    access_key=bucket_access_key,
                    secret_key=bucket_secret_key,
                    endpoint=config.cloudflare.r2_endpoint,
                    session_token=bucket_session_token,
                    bucket_name=activity_input.bucket_name,
                )

                prefix = activity_input.dest_dir.split("/")[-1]
                if prefix:
                    delete_files_from_cloudflare(
                        tenant=activity_input.tenant,
                        input_path=f"{activity_input.bucket_name}/{prefix}",
                        endpoint=config.cloudflare.r2_endpoint,
                        access_key=bucket_access_key,
                        secret_key=bucket_secret_key,
                        session_token=bucket_session_token,
                    )

                await sync_and_verify_files(
                    op=storage_client,
                    input_path=os.path.join(opendal_file_operations.tempdir_root, tmp_dir, activity_input.bundle_path),
                    bucket_name=activity_input.bucket_name,
                    dest_dir=activity_input.dest_dir,
                    prefix=prefix,
                )

                log_info(f"UI setup completed for {activity_input.dest_dir}")

        except Exception as e:
            log_error(f"Error downloading UI bundle: {e}")
            raise e


class CopyWebCoreToBucketActivity(Activity):
    """
    CopyWebCoreToBucketActivity
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
    @activity.defn(name="CopyWebCoreToBucketActivity")
    async def defn(activity_input: CopyWebCoreToBucketActivityModel) -> None:
        """
        Copy webcore to a bucket
        """
        from app.cli.cloudflare_utils import get_temporary_credentials

        config: AppSettings = get_settings()

        bucket_temporary_credentials = await get_temporary_credentials(config, activity_input.bucket_name)
        bucket_access_key = bucket_temporary_credentials.access_key_id
        bucket_secret_key = bucket_temporary_credentials.secret_access_key

        artifacts_access_key = config.cloudflare.r2_access_key
        artifacts_secret_key = config.cloudflare.r2_secret_key
        artifacts_s3_client = get_s3_client(
            access_key=artifacts_access_key,
            secret_key=artifacts_secret_key,
            endpoint=config.cloudflare.r2_endpoint,
            bucket_name="artifacts",
        )
        try:
            opendal_file_operations = get_opendal_file_client()
            async with opendal_file_operations.temp_dir() as tmp_dir:
                temp_file_path = os.path.join(opendal_file_operations.tempdir_root, tmp_dir, activity_input.bundle_name)

                await download_file_from_storage(
                    object_name=activity_input.src_object_name,
                    file_path=temp_file_path,
                    storage_client=artifacts_s3_client,
                )

                copy_files_to_cloudflare(
                    tenant=activity_input.tenant,
                    input_path=temp_file_path,
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


class DeleteCloudflareBucketActivity(Activity):
    """
    DeleteCloudflareBucketActivity
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
    @activity.defn(name="DeleteCloudflareBucketActivity")
    async def defn(activity_input: DeleteCloudflareBucketActivityModel) -> None:
        """
        Delete a Cloudflare bucket
        """
        from app.cli.cloudflare_utils import delete_bucket

        config: AppSettings = get_settings()

        try:
            await delete_bucket(config=config, bucket_name=activity_input.bucket_name)
        except Exception as e:
            log_error(f"Error deleting bucket {activity_input.bucket_name}: {e}")


class DeleteFilesFromCloudflareActivity(Activity):
    """
    DeleteFilesFromCloudflareActivity
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
    @activity.defn(name="DeleteFilesFromCloudflareActivity")
    async def defn(activity_input: DeleteFilesFromCloudflareActivityModel) -> None:
        """
        Delete files from Cloudflare
        """
        from app.cli.cloudflare_utils import get_temporary_credentials

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
        return RetryPolicy(initial_interval=timedelta(seconds=10), maximum_attempts=5, backoff_coefficient=3)

    @staticmethod
    @activity.defn(name="DeleteCloudflareDNSRecordActivity")
    async def defn(activity_input: DeleteCloudflareDNSRecordActivityModel) -> None:
        """
        Delete a Cloudflare DNS record
        """
        from app.cli.cloudflare_utils import delete_dns_record

        config: AppSettings = get_settings()

        try:
            await delete_dns_record(config=config, fqdn=activity_input.domain_name, zone_id=activity_input.zone_id)
        except Exception as e:
            log_error(f"Error deleting DNS record {activity_input.domain_name}: {e}")


class PropagateDNSRecordActivity(Activity):
    """
    PropagateDNSRecordActivity
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
                    raise TimeoutError(f"DNS propagation check timed out after [10 min]: {activity_input.domain_name}")
                log_info(f"DNS not propagated yet: {activity_input.domain_name}")
                await asyncio.sleep(10)


class PenknifeCopyArtifactsToBucketActivity(Activity):
    """
    PenknifeCopyArtifactsToBucketActivity
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
    @activity.defn(name="PenknifeCopyArtifactsToBucketActivity")
    async def defn(activity_input: PenknifeCopyArtifactsToBucketActivityModel) -> None:
        """
        Copy artifacts to a bucket
        """
        from app.cli.cloudflare_utils import get_temporary_credentials

        config: AppSettings = get_settings()

        environment: str = config.env

        artifacts_access_key = config.cloudflare.r2_access_key
        artifacts_secret_key = config.cloudflare.r2_secret_key

        artifacts_s3_client = get_s3_client(
            access_key=artifacts_access_key,
            secret_key=artifacts_secret_key,
            endpoint=config.cloudflare.r2_endpoint,
            bucket_name="artifacts",
        )

        try:
            opendal_file_operations = get_opendal_file_client()
            async with opendal_file_operations.temp_dir() as tmp_dir:
                temp_file_path = os.path.join(opendal_file_operations.tempdir_root, tmp_dir, activity_input.bundle_name)

                await download_file_from_storage(
                    object_name=activity_input.src_object_name,
                    file_path=temp_file_path,
                    storage_client=artifacts_s3_client,
                )

                # unzip the file
                with zipfile.ZipFile(temp_file_path, "r") as zip_ref:
                    zip_ref.extractall(os.path.join(opendal_file_operations.tempdir_root, tmp_dir, "bundle"))

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
                    input_path=os.path.join(opendal_file_operations.tempdir_root, tmp_dir, "bundle/dist"),
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

                # delete_files_from_cloudflare(
                #     tenant=activity_input.tenant,
                #     input_path=f"{activity_input.careerportal_bucket_name}/",
                #     endpoint=config.cloudflare.r2_endpoint,
                #     access_key=bucket_access_key,
                #     secret_key=bucket_secret_key,
                #     session_token=bucket_temporary_credentials.session_token,
                # )

                storage_client = get_s3_client(
                    access_key=bucket_access_key,
                    secret_key=bucket_secret_key,
                    endpoint=config.cloudflare.r2_endpoint,
                    session_token=bucket_temporary_credentials.session_token,
                    bucket_name=activity_input.careerportal_bucket_name,
                )

                # copy "apply" directory
                await sync_and_verify_files(
                    op=storage_client,
                    input_path=os.path.join(
                        opendal_file_operations.tempdir_root,
                        tmp_dir,
                        "bundle",
                        "dist",
                        "careerpages",
                        "apply",
                    ),
                    bucket_name=activity_input.careerportal_bucket_name,
                    dest_dir="",
                    prefix="apply",
                )
                # copy "public" directory
                await sync_and_verify_files(
                    op=storage_client,
                    input_path=os.path.join(
                        opendal_file_operations.tempdir_root,
                        tmp_dir,
                        "bundle",
                        "dist",
                        "careerpages",
                        "public",
                    ),
                    bucket_name=activity_input.careerportal_bucket_name,
                    prefix="public",
                    dest_dir="",
                )

                log_info(f"UI setup completed for {activity_input.tenant}")

        except Exception as e:
            log_error(f"Error downloading UI bundle: {e}")
            raise e


class UpdateCORSForBucketActivity(Activity):
    """
    UpdateCORSForBucketActivity
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
    @activity.defn(name="UpdateCORSForBucketActivity")
    async def defn(activity_input: UpdateCORSForBucketActivityModel) -> None:
        """
        Update CORS for a bucket
        """
        from app.cli.cloudflare_utils import update_cors_for_bucket

        config: AppSettings = get_settings()
        await update_cors_for_bucket(config=config, bucket_name=activity_input.bucket_name, rules=activity_input.rules)


class CreateCloudflareBucketCredentialsActivity(Activity):
    """
    CreateCloudflareBucketCredentialsActivity
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
    @activity.defn(name="CreateCloudflareBucketCredentialsActivity")
    async def defn(activity_input: CreateCloudflareBucketCredentialsActivityModel) -> CloudflareBucketCredentials:
        """
        Create Cloudflare bucket credentials
        """
        from app.cli.cloudflare_utils import create_cloudflare_bucket_credentials

        config: AppSettings = get_settings()
        return await create_cloudflare_bucket_credentials(
            bucket_name=activity_input.bucket_name, config=config, read_only=activity_input.read_only
        )


class WorkersKVConfigUploadActivity(Activity):
    """
    WorkersKVConfigUploadActivity
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
    @activity.defn(name="WorkersKVConfigUploadActivity")
    async def defn(activity_input: WorkersKVConfigUploadActivityModel) -> None:
        """
        Fetch the Workers KV template from R2, render Jinja with `template_payload`, inject
        1Password secrets, then upload the resulting string to Cloudflare Workers KV.
        """
        from app.cli.cloudflare_utils import workers_kv_config_upload

        config: AppSettings = get_settings()
        # Same bucket the K8sConfigMapCreationActivity R2 path reads from, so a product keeps all
        # of its templates under one prefix.
        s3_client = get_s3_client(
            access_key=config.cloudflare.r2_access_key,
            secret_key=config.cloudflare.r2_secret_key,
            endpoint=config.cloudflare.r2_endpoint,
            bucket_name="launchpad-config-templates",
        )

        opendal_file_operations = get_opendal_file_client()
        async with opendal_file_operations.temp_dir() as temp_dir:
            temp_dir_path = os.path.join(opendal_file_operations.tempdir_root, temp_dir)
            template_path = os.path.join(temp_dir_path, activity_input.template_file_name)

            await download_file_from_storage(
                object_name=f"{activity_input.cloudflare_r2_folder_path}/{activity_input.template_file_name}",
                file_path=template_path,
                storage_client=s3_client,
            )

            template_env = get_env(template_path=temp_dir_path)
            template = template_env.get_template(activity_input.template_file_name)
            rendered = template.render(**activity_input.template_payload)

            await opendal_file_operations.write_file(template_path, rendered)

            injected_path = os.path.join(temp_dir_path, f"injected_{activity_input.template_file_name}")
            await secret_inject_drop_empty(source_file_path=template_path, destination_path=injected_path)

            value = await opendal_file_operations.read_file_str(injected_path)

        await workers_kv_config_upload(
            config=config,
            namespace_id=activity_input.namespace_id,
            key=activity_input.key,
            value=value,
        )


class AddBucketsToR2TokenActivity(Activity):
    """
    AddBucketsToR2TokenActivity - extend an existing R2 user token's bucket scope to grant
    write access to additional buckets. Idempotent; no-op if the token does not exist.
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(minutes=2)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(initial_interval=timedelta(seconds=10), maximum_attempts=5, backoff_coefficient=3)

    @staticmethod
    @activity.defn(name="AddBucketsToR2TokenActivity")
    async def defn(activity_input: AddBucketsToR2TokenActivityModel) -> None:
        """
        Add bucket access (write by default, read-only when `read_only=True`) to an
        existing R2 token's scope.
        """
        from app.cli.cloudflare_utils import add_buckets_to_token

        config: AppSettings = get_settings()
        await add_buckets_to_token(
            config=config,
            token_name=activity_input.token_name,
            bucket_names=activity_input.bucket_names,
            read_only=activity_input.read_only,
        )
