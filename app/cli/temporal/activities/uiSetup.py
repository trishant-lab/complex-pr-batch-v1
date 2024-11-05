from temporalio import activity, workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from datetime import timedelta
    import tempfile
    import zipfile
    import boto3

    from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
    from app.cli.temporal.core.log import log_error, log_info
    from app.core.settings import AppSettings, get_settings
    from app.s3_utils import copy_files_to_s3, download_file_from_storage, get_storage_client


class UiSetupActivityModel(LaunchpadCLIBaseModel):
    """
    UiSetupActivityModel
    """

    src_object_name: str
    dest_dir: str
    bundle_path: str


class UiSetupActivity(Activity):
    """
    UiSetupActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

    @staticmethod
    @activity.defn(name="UiSetupActivity")
    async def defn(activity_model: UiSetupActivityModel) -> None:
        """
        Callable for the activity
        """
        config: AppSettings = get_settings()

        environment: str = config.env

        s3_int_client: boto3.client = get_storage_client(
            config=config,
            access_key=config.s3_int.access_key,
            secret_key=config.s3_int.secret_key,
            endpoint=config.s3_int.endpoint,
        )

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                download_file_from_storage(
                    object_name=activity_model.src_object_name,
                    file_path=f"{tmp_dir}/bundle.zip",
                    storage_client=s3_int_client,
                    bucket_name="artifacts",
                )

                # unzip the file
                with zipfile.ZipFile(f"{tmp_dir}/bundle.zip", "r") as zip_ref:
                    zip_ref.extractall(f"{tmp_dir}/bundle")

                # copy the files to the destination directory
                copy_files_to_s3(
                    input_path=f"{tmp_dir}/{activity_model.bundle_path}",
                    output_path=f"{config.s3.rclone_remote}/static/{activity_model.dest_dir}",
                    config=config,
                )

                # todo: check if this is needed for all products
                if environment == "production":
                    copy_files_to_s3(
                        input_path=f"{tmp_dir}/{activity_model.bundle_path}/index.html",
                        output_path=f"{config.s3.rclone_remote}/static/{activity_model.dest_dir}/custom/index.html",
                        config=config,
                    )

                log_info(f"UI setup completed for {activity_model.dest_dir}")

        except Exception as e:
            log_error(f"Error downloading UI bundle: {e}")
            raise e
