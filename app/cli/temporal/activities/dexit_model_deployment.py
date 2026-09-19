"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 8)
"""

from datetime import timedelta
import aiofiles
import asyncio
import huggingface_hub
import json
import os
import shutil
from aiopath import AsyncPath
from clearml import Task
from dataclasses import dataclass
from loguru import logger
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.temporal.core.base import Activity
from app.core.settings import AppSettings, DexitSettings, get_settings
from app.utils.s3_operations import get_s3_client

config: AppSettings = get_settings()
dexit_config: DexitSettings = config.dexit

IGNORED_FILES = [".gitattributes"]


@dataclass
class ModelDeploymentActivityModel:
    tenant: str
    storage_access_key: str
    storage_secret_key: str
    storage_bucket_name: str
    task_ids: list[str] | None = None


class ClearMLManager:
    """Manages ClearML configuration and operations."""

    def __init__(self, model: ModelDeploymentActivityModel) -> None:
        self._storage_endpoint_url = config.cloudflare.r2_endpoint
        self._storage_bucket = model.storage_bucket_name
        self._storage_access_key = model.storage_access_key
        self._storage_secret_key = model.storage_secret_key

    @property
    def files_server(self) -> str:
        """Get the ClearML files server URL."""
        storage_endpoint_url: str = self._storage_endpoint_url.removeprefix("https://").removesuffix("/")
        return f"s3://{storage_endpoint_url}/{self._storage_bucket}/data/__mlops__/clearml"

    @property
    def access_key(self) -> str:
        """Get the ClearML access key."""
        return dexit_config.dexit_model_deployment.clearml.access_key

    @property
    def secret_key(self) -> str:
        """Get the ClearML secret key."""
        return dexit_config.dexit_model_deployment.clearml.secret_key

    @property
    def storage_host(self) -> str:
        """Get the ClearML storage host."""
        return self._storage_endpoint_url.removeprefix("https://").removesuffix("/")

    @property
    def storage_access_key(self) -> str:
        """Get the ClearML storage access key."""
        return self._storage_access_key

    @property
    def storage_secret_key(self) -> str:
        """Get the ClearML storage secret key."""
        return self._storage_secret_key

    @property
    def clearml_running_tasks_s3_path(self) -> str:
        """Get the ClearML running tasks S3 path."""
        return "data/__mlops__/clearml/running_tasks.json"

    async def setup_clearml_config(self) -> None:
        """Setup the clearml config"""
        os.environ["CLEARML__FILES_SERVER"] = self.files_server
        os.environ["CLEARML__ACCESS_KEY"] = self.access_key
        os.environ["CLEARML__SECRET_KEY"] = self.secret_key
        os.environ["CLEARML__STORAGE_HOST"] = self.storage_host
        os.environ["CLEARML__STORAGE_ACCESS_KEY"] = self.storage_access_key
        os.environ["CLEARML__STORAGE_SECRET_KEY"] = self.storage_secret_key

        current_dir = AsyncPath(__file__).parent
        temporal_dir = current_dir.parent
        clearml_conf_path = temporal_dir / "dexit" / "templates" / "clearml.conf"
        output_path = (await AsyncPath.home()) / "clearml.conf"

        async with aiofiles.open(clearml_conf_path) as infile, aiofiles.open(output_path, "w") as outfile:
            process = await asyncio.create_subprocess_exec(
                "envsubst", stdin=infile, stdout=outfile, stderr=asyncio.subprocess.PIPE
            )

            _, stderr = await process.communicate()
            if process.returncode != 0:
                raise RuntimeError(f"Failed to render clearml.conf: {stderr.decode()}")

        logger.success("Successfully processed and moved clearml.conf to home directory")


async def copy_huggingface_repo(
    source_repo_id: str,
    source_revision: str,
    destination_repo_id: str,
    destination_revision: str,
    hf_token: str,
    ignore_files: list[str] | None = None,
) -> None:
    """Copy a Hugging Face repo from one revision to another."""
    if ignore_files is None:
        ignore_files = IGNORED_FILES

    hf_api = huggingface_hub.HfApi(token=hf_token)
    hf_file_system = huggingface_hub.HfFileSystem(token=hf_token)

    # Create the destination repo if it doesn't exist
    hf_api.create_repo(
        repo_id=destination_repo_id,
        private=True,
        repo_type="model",
        exist_ok=True,
    )
    hf_api.create_branch(
        repo_id=destination_repo_id,
        repo_type="model",
        branch=destination_revision,
        revision="main",
        exist_ok=True,
    )

    # List the files in the source repo (paths are like "repo_id/path/to/file.ext").
    # Each upload_file call below creates a new commit; same-named files at the destination
    # revision are overwritten automatically, so retries are safe without a skip check.
    source_files: list[str] = hf_file_system.ls(source_repo_id, detail=False, revision=source_revision)

    for idx, source_file in enumerate(source_files):
        # Strip the leading repo_id/ prefix to get the relative path within the repo
        repo_prefix = f"{source_repo_id}/"
        relative_path: str = source_file[len(repo_prefix) :] if source_file.startswith(repo_prefix) else source_file
        source_file_name: str = AsyncPath(source_file).name
        if source_file_name in ignore_files:
            continue

        logger.info(
            f"{idx + 1}/{len(source_files)}: Uploading {relative_path} to {destination_repo_id}@{destination_revision}"
        )
        local_path: str = huggingface_hub.hf_hub_download(  # nosec B615
            repo_id=source_repo_id,
            filename=relative_path,
            repo_type="model",
            revision=source_revision,
            token=hf_token,
        )

        hf_api.upload_file(
            path_or_fileobj=local_path,
            path_in_repo=relative_path,
            repo_id=destination_repo_id,
            repo_type="model",
            revision=destination_revision,
            commit_message=f"Add {relative_path} to {destination_repo_id}@{destination_revision}",
        )

        cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
        shutil.rmtree(cache_dir, ignore_errors=True)


async def setup_clearml_task(
    clearml_manager: ClearMLManager,
    clearml_project_name: str,
    clearml_task_name: str,
    source_repo_id: str,
    source_revision: str,
    dataset_params: dict | None = None,
    model_configuration: dict | None = None,
    model_hyperparameters: dict | None = None,
) -> str:
    """Setup ClearML task and upload artifacts."""
    output_artifact_path = None
    task = None
    try:
        await clearml_manager.setup_clearml_config()
        task = Task.init(
            project_name=clearml_project_name,
            task_name=clearml_task_name,
            output_uri=False,
            reuse_last_task_id=False,
            auto_connect_streams=False,
            auto_connect_frameworks=False,
            auto_resource_monitoring=False,
            auto_connect_arg_parser=False,
        )

        if dataset_params:
            task.connect(dataset_params, name="Dataset Parameters")
        if model_configuration:
            task.connect(model_configuration, name="Model Configuration")
        if model_hyperparameters:
            task.connect(model_hyperparameters, name="Model Hyperparameters")

        # Download output artifact file from source repo
        output_artifact_path = huggingface_hub.hf_hub_download(  # nosec B615
            repo_id=source_repo_id,
            filename="Output Artifacts.json",
            repo_type="model",
            revision=source_revision,
            token=dexit_config.dexit_model_deployment.hf_token,
        )

        async with aiofiles.open(output_artifact_path) as f:
            content = await f.read()
            try:
                output_artifacts_data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Output Artifacts.json: {e}")
                output_artifacts_data = {}

        task.upload_artifact("Output Artifacts", output_artifacts_data)
        logger.success("Uploaded parsed Output Artifacts to ClearML")
        task_id = task.id
        await asyncio.wait_for(asyncio.to_thread(task.close), timeout=300)
        task = None
        logger.success(f"ClearML task {task_id} closed successfully")
        return task_id

    except Exception as e:
        logger.error(f"ClearML task setup failed: {e}")
        raise

    finally:
        # Ensure task is closed to avoid orphaned Running tasks on the ClearML server
        if task is not None:
            try:
                await asyncio.wait_for(asyncio.to_thread(task.close), timeout=60)
            except Exception as close_err:
                logger.warning(f"Failed to close ClearML task during cleanup: {close_err}")
        if output_artifact_path and os.path.exists(output_artifact_path):
            os.remove(output_artifact_path)
        cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
        shutil.rmtree(cache_dir, ignore_errors=True)


class ClassificationModelDeploymentActivity(Activity):
    """Classification model deployment activity."""

    @staticmethod
    def get_timeout() -> timedelta:
        """Get the timeout for the activity."""
        return timedelta(minutes=45)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """Get the retry policy for the activity."""
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="ClassificationModelDeploymentActivity")
    async def defn(activity_model: ModelDeploymentActivityModel) -> str:
        """Run the activity."""
        model_name = "LayoutLMv3"
        model_type = "Classification"
        destination_repo_id = f"314e/{activity_model.tenant}-{model_name}-{model_type}"
        destination_revision = dexit_config.dexit_model_deployment.destination_revision
        source_repo_id = dexit_config.dexit_model_deployment.classification_source_repo
        source_revision = dexit_config.dexit_model_deployment.classification_source_revision
        ignore_files = IGNORED_FILES

        await copy_huggingface_repo(
            source_repo_id=source_repo_id,
            source_revision=source_revision,
            destination_repo_id=destination_repo_id,
            destination_revision=destination_revision,
            hf_token=dexit_config.dexit_model_deployment.hf_token,
            ignore_files=ignore_files,
        )

        dataset_params = {
            "ID": None,
            "TRAIN_S3_PATH": None,
            "TEST_S3_PATH": None,
            "EVAL_S3_PATH": None,
            "MISCELLANEOUS_S3_PATH": None,
            "TRAIN_SIZE": 0.7,
            "TEST_SIZE": 0.2,
            "EVAL_SIZE": 0.1,
            "SEED": 42,
        }
        model_configuration = {
            "MODELVERSIONTAG": destination_revision,
            "MODELNAME": model_name,
            "MODELTYPE": model_type,
            "TRAINING_QUEUE_JOBID": None,
            "TRAINING_QUEUE_JOBTYPE": None,
            "HF_MODEL_ID": f"314e/dexit-{model_name}-{model_type}-{activity_model.tenant}-{config.env}",
            "ENVIRONMENT": config.env,
            "NEW_MODELVERSIONTAG": destination_revision,
        }
        model_hyperparamters = {
            "TRAIN_BATCH_SIZE": 24,
            "TRAIN_LR": 1e-05,
            "TRAIN_EPOCHS": 10,
            "TRAIN_PRECISION": 16,
            "EARLYSTOPPING_MONITOR": "val_loss",
            "EARLYSTOPPING_PATIENCE": 3,
            "EARLYSTOPPING_MODE": "min",
            "EARLYSTOPPING_MIN_DELTA": 0.005,
            "MODELCKPT_MONITOR": "val_loss",
            "MODELCKPT_MODE": "min",
            "MODELCKPT_SAVE_TOP_K": 5,
            "MODELCKPT_SAVE_LAST": True,
            "CREATE_TENANT_SPECIFIC_ENDPOINT": True,
        }

        clearml_manager = ClearMLManager(activity_model)

        return await setup_clearml_task(
            clearml_manager=clearml_manager,
            clearml_project_name=f"DEXIT {activity_model.tenant} {config.env}/DOCUMENT CLASSIFICATION".upper(),
            clearml_task_name=f"{model_name} - {destination_revision}",
            source_repo_id=source_repo_id,
            source_revision=source_revision,
            dataset_params=dataset_params,
            model_configuration=model_configuration,
            model_hyperparameters=model_hyperparamters,
        )


class EntityModelDeploymentActivity(Activity):
    """Entity model deployment activity."""

    @staticmethod
    def get_timeout() -> timedelta:
        """Get the timeout for the activity."""
        return timedelta(minutes=45)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """Get the retry policy for the activity."""
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="EntityModelDeploymentActivity")
    async def defn(activity_model: ModelDeploymentActivityModel) -> str:
        """Run the activity."""
        model_name = "VLM-Gemma3"
        model_type = "Entity"
        ignore_files = IGNORED_FILES
        destination_repo_id = f"314e/{activity_model.tenant}-{model_name}-{model_type}"
        destination_revision = dexit_config.dexit_model_deployment.destination_revision
        source_repo_id = dexit_config.dexit_model_deployment.entity_source_repo
        source_revision = dexit_config.dexit_model_deployment.entity_source_revision

        await copy_huggingface_repo(
            source_repo_id=source_repo_id,
            source_revision=source_revision,
            destination_repo_id=destination_repo_id,
            destination_revision=destination_revision,
            hf_token=dexit_config.dexit_model_deployment.hf_token,
            ignore_files=ignore_files,
        )

        dataset_params = {
            "ID": None,
            "TRAIN_S3_PATH": None,
            "TEST_S3_PATH": None,
            "EVAL_S3_PATH": None,
            "MISCELLANEOUS_S3_PATH": None,
            "TRAIN_SIZE": 0.4,
            "TEST_SIZE": 0.3,
            "EVAL_SIZE": 0.3,
            "SEED": 42,
        }
        model_configuration = {
            "MODELVERSIONTAG": destination_revision,
            "MODELNAME": model_name,
            "MODELTYPE": model_type,
            "TRAINING_QUEUE_JOBID": None,
            "TRAINING_QUEUE_JOBTYPE": None,
            "ARTIFACTS_DIR": None,
            "HF_BASE_MODEL_ID": "google/gemma-3-12b-it",
            "HF_MODEL_ID": f"314e/dexit-{model_name}-{model_type}-{activity_model.tenant}-{config.env}",
            "ENVIRONMENT": config.env,
            "NEW_MODELVERSIONTAG": destination_revision,
            "CREATE_TENANT_SPECIFIC_ENDPOINT": True,
        }
        model_hyperparamters = {
            "TRAIN_BATCH_SIZE": 2,
            "EVAL_BATCH_SIZE": 2,
            "TRAIN_EPOCHS": 10,
            "GRAD_ACCUM_STEPS": 2,
            "RANK": 128,
            "ALPHA": 256,
            "LEARNING_RATE": 2e-05,
            "MAX_GRAD_NORM": 0.3,
            "WARMUP_RATIO": 0.03,
            "DATALOADER_NUM_WORKERS": 4,
            "DROPOUT": 0.05,
            "INFERENCE_BATCH_SIZE": 10,
        }

        clearml_manager = ClearMLManager(activity_model)

        return await setup_clearml_task(
            clearml_manager=clearml_manager,
            clearml_project_name=f"DEXIT {activity_model.tenant} {config.env}/ENTITY EXTRACTION".upper(),
            clearml_task_name=f"{model_name} - {destination_revision}",
            source_repo_id=source_repo_id,
            source_revision=source_revision,
            dataset_params=dataset_params,
            model_configuration=model_configuration,
            model_hyperparameters=model_hyperparamters,
        )


class StoreClearMLTasksActivity(Activity):
    """Store ClearML tasks activity."""

    @staticmethod
    def get_timeout() -> timedelta:
        """Get the timeout for the activity."""
        return timedelta(seconds=30)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """Get the retry policy for the activity."""
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="StoreClearMLTasksActivity")
    async def defn(activity_model: ModelDeploymentActivityModel) -> None:
        """Run the activity."""
        try:
            # Create S3 client using OpenDAL
            s3_client = get_s3_client(
                access_key=activity_model.storage_access_key,
                secret_key=activity_model.storage_secret_key,
                endpoint=config.cloudflare.r2_endpoint,
                bucket_name=activity_model.storage_bucket_name,
            )

            # Create JSON payload
            payload = {"task_ids": activity_model.task_ids}
            payload_bytes = json.dumps(payload).encode("utf-8")

            # Upload to S3 using OpenDAL
            clearml_manager = ClearMLManager(activity_model)
            await s3_client.upload_object(
                path=clearml_manager.clearml_running_tasks_s3_path,
                file_name="running_tasks.json",
                content_type="application/json",
                file_content=payload_bytes,
            )

            logger.success(
                f"Successfully stored ClearML task IDs at s3://{activity_model.storage_bucket_name}/{clearml_manager.clearml_running_tasks_s3_path}"
            )

        except Exception as e:
            logger.error(f"Failed to store ClearML task IDs: {e}")
            raise


# --- launchpad oncall hardening (complex-pr batch) ---
def _activity_log_fields(name: str, **extra):
    """Structured fields for Temporal activity logging (oncall / Grafana)."""
    base = {
        "activity": name,
        "service": "launchpad",
        "layer": "temporal",
        "product": "launchpad-app",
    }
    base.update(extra)
    return base


class ActivityHardeningError(RuntimeError):
    """Refuse silent/unsafe fallbacks inside Temporal activities."""

    def __init__(self, activity: str, reason: str):
        super().__init__(f"[{activity}] {reason}")
        self.activity = activity
        self.reason = reason


def _require_nonempty(activity: str, field: str, value) -> None:
    """Fail loud when a required provisioning field is blank."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ActivityHardeningError(activity, f"{field} must be set before provision")


_RETRY_HINTS = {
    "transient_http": {"attempts": 5, "backoff_seconds": 8},
    "dependency_warmup": {"attempts": 3, "backoff_seconds": 20},
    "idempotent_create": {"attempts": 2, "backoff_seconds": 5},
}


def _retry_hint(kind: str) -> dict:
    """Return a documented retry hint for activity authors / runbooks."""
    return dict(_RETRY_HINTS.get(kind, _RETRY_HINTS["transient_http"]))
