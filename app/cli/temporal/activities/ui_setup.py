from temporalio import activity
from temporalio.common import RetryPolicy


from datetime import timedelta
import tempfile
import zipfile

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_error, log_info
from app.core.settings import AppSettings, get_settings
from app.s3_utils import copy_files_to_s3, download_file_from_storage
from app.utils.s3_operations import get_s3_client


class UiSetupActivityModel(LaunchpadCLIBaseModel):
    """
    UiSetupActivityModel
    """

    src_object_name: str
    dest_dir: str
    bundle_path: str
    bundle_name: str


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
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="UiSetupActivity")
    async def defn(activity_model: UiSetupActivityModel) -> None:
        """
        Callable for the activity
        """
        config: AppSettings = get_settings()

        environment: str = config.env

        s3_int_client = get_s3_client(
            access_key=config.s3_int.access_key,
            secret_key=config.s3_int.secret_key,
            endpoint=config.s3_int.endpoint,
            bucket_name="artifacts",
        )

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                await download_file_from_storage(
                    object_name=activity_model.src_object_name,
                    file_path=f"{tmp_dir}/{activity_model.bundle_name}",
                    storage_client=s3_int_client,
                )

                # unzip the file
                with zipfile.ZipFile(f"{tmp_dir}/{activity_model.bundle_name}", "r") as zip_ref:
                    zip_ref.extractall(f"{tmp_dir}/bundle")

                # copy the files to the destination directory
                copy_files_to_s3(
                    input_path=f"{tmp_dir}/{activity_model.bundle_path}",
                    output_path=f"{config.s3.s3_alias}/static/{activity_model.dest_dir}",
                    config=config,
                )

                if environment == "production":
                    copy_files_to_s3(
                        input_path=f"{tmp_dir}/{activity_model.bundle_path}/index.html",
                        output_path=f"{config.s3.s3_alias}/static/{activity_model.dest_dir}/custom/index.html",
                        config=config,
                    )

                log_info(f"UI setup completed for {activity_model.dest_dir}")

        except Exception as e:
            log_error(f"Error downloading UI bundle: {e}")
            raise e
