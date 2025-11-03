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

IGNORED_FILES = [".git", ".gitattributes"]

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
        storage_endpoint_url: str = self._storage_endpoint_url.removeprefix('https://').removesuffix('/')
        return f's3://{storage_endpoint_url}/{self._storage_bucket}/data/__mlops__/clearml'

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
        return self._storage_endpoint_url.removeprefix('https://').removesuffix('/')

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
        os.environ['CLEARML__FILES_SERVER'] = self.files_server
        os.environ['CLEARML__ACCESS_KEY'] = self.access_key
        os.environ['CLEARML__SECRET_KEY'] = self.secret_key
        os.environ['CLEARML__STORAGE_HOST'] = self.storage_host
        os.environ['CLEARML__STORAGE_ACCESS_KEY'] = self.storage_access_key
        os.environ['CLEARML__STORAGE_SECRET_KEY'] = self.storage_secret_key

        current_dir = AsyncPath(__file__).parent
        temporal_dir = current_dir.parent
        clearml_conf_path = temporal_dir / 'dexit' / 'templates' / 'clearml.conf'
        output_path = (await AsyncPath.home()) / 'clearml.conf'

        try:
            # Open files manually for I/O redirection
            async with aiofiles.open(clearml_conf_path) as infile, aiofiles.open(output_path, 'w') as outfile:
                process = await asyncio.create_subprocess_exec(
                    'envsubst',
                    stdin=infile,
                    stdout=outfile,
                    stderr=asyncio.subprocess.PIPE
                )

                _, stderr = await process.communicate()
                if process.returncode != 0:
                    raise RuntimeError(stderr.decode())  # noqa: TRY301

            logger.success("Successfully processed and moved clearml.conf to home directory")

        except Exception as e:
            logger.error(f"Error executing command: {e}")


async def copy_huggingface_repo(
    source_repo_id: str,
    source_revision: str,
    destination_repo_id: str,
    destination_revision: str,
    hf_token: str,
    ignore_files: list[str] | None = None
) -> None:
    """Copy a Hugging Face repo from one revision to another."""
    if ignore_files is None:
        ignore_files = IGNORED_FILES

    hf_api = huggingface_hub.HfApi(token=hf_token)

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

    # List the files in the source repo
    hf_file_system = huggingface_hub.HfFileSystem(token=hf_token)
    source_files: list[str] = hf_file_system.ls(source_repo_id, detail=False, revision=source_revision)

    for idx, source_file in enumerate(source_files):
        source_file_name: str = AsyncPath(source_file).name
        if source_file_name in ignore_files:
            continue

        logger.info(
            f"{idx+1}/{len(source_files)}: Uploading {source_file} to {destination_repo_id}@{destination_revision}"
        )
        local_path: str = huggingface_hub.hf_hub_download( # nosec B615
            repo_id=source_repo_id,
            filename=source_file_name,
            repo_type="model",
            revision=source_revision,
            token=hf_token
        )

        hf_api.upload_file(
            path_or_fileobj=local_path,
            path_in_repo=source_file_name,
            repo_id=destination_repo_id,
            repo_type="model",
            revision=destination_revision,
            commit_message=f"Add {source_file} to {destination_repo_id}@{destination_revision}"
        )

        cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
        shutil.rmtree(cache_dir, ignore_errors=True)

async def setup_clearml_task(
    clearml_manager: ClearMLManager,
    clearml_project_name: str,
    clearml_task_name: str,
    source_repo_id: str,
    source_revision: str,
    params: dict | None = None
) -> str:
    """Setup ClearML task and upload artifacts."""
    output_artifact_path = None
    try:
        await clearml_manager.setup_clearml_config()
        task = Task.init(
            project_name=clearml_project_name,
            task_name=clearml_task_name,
            output_uri=clearml_manager.files_server
        )

        if params:
            task.connect(params)

        # Download output artifact file from source repo
        output_artifact_path = huggingface_hub.hf_hub_download( # nosec B615
            repo_id=source_repo_id,
            filename="Output Artifacts.json",
            repo_type="model",
            revision=source_revision,
            token=dexit_config.dexit_model_deployment.hf_token
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
        task.close()
        return task_id

    except Exception as e:
        logger.error(f'Error initializing ClearMLManager: {e}')
        raise

    finally:
        if output_artifact_path and os.path.exists(output_artifact_path):
            os.remove(output_artifact_path)
        cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
        shutil.rmtree(cache_dir, ignore_errors=True)


class ClassificationModelDeploymentActivity(Activity):
    """Classification model deployment activity."""

    @staticmethod
    def get_timeout() -> timedelta:
        """Get the timeout for the activity."""
        return timedelta(minutes=10)

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
            ignore_files=ignore_files
        )

        params = {
            "DATASET_EVAL_SIZE": 0.1,
            "DATASET_JSON_S3PATH": '',
            "DATASET_TEST_SIZE": 0.2,
            "DATASET_TRAIN_SIZE": 0.7,
            "EARLYSTOPPING_MIN_DELTA": 0.005,
            "EARLYSTOPPING_MODE": 'min',
            "EARLYSTOPPING_MONITOR": 'val_loss',
            "EARLYSTOPPING_PATIENCE": 4,
            "ENVIRONMENT": config.env,
            "HF_MODEL_ID": destination_repo_id,
            "LIMIT_SAMPLES_PER_CLASS": -1,
            "MODELCKPT_MODE": 'min',
            "MODELCKPT_MONITOR": 'val_loss',
            "MODELCKPT_SAVE_LAST": True,
            "MODELCKPT_SAVE_TOP_K": 3,
            "MODELNAME": model_name,
            "MODELTYPE": model_type,
            "MODELVERSIONTAG": source_revision,
            "NEW_MODELVERSIONTAG": destination_revision,
            "REMOVE_DOCTYPES": [],
            "REMOVE_FOLDERS_HAVING_LESS_THAN_N_DOCUMENTS": 5,
            "SEED": 42,
            "TRAIN_BATCH_SIZE": 24,
            "TRAIN_EPOCHS": 2,
            "TRAIN_LR": 1e-05,
            "TRAIN_PRECISION": 16,
            "TRAINING_QUEUE_JOBID": '',
            "TRAINING_QUEUE_JOBTYPE": ''
        }

        clearml_manager = ClearMLManager(activity_model)

        return await setup_clearml_task(
            clearml_manager=clearml_manager,
            clearml_project_name=f"dexit-{activity_model.tenant}/Document Classification",
            clearml_task_name=f"{model_name} - {destination_revision}",
            source_repo_id=source_repo_id,
            source_revision=source_revision,
            params=params
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
            ignore_files=ignore_files
        )

        params = {
            "ALPHA": 250,
            "DATASET_EVAL_SIZE": 0.1,
            "DATASET_JSON_S3PATH": "",
            "DATASET_TEST_SIZE": 0.2,
            "DATASET_TRAIN_SIZE": 0.71,
            "ENVIRONMENT": config.env,
            "GRAD_ACCUM_STEPS": 40,
            "HF_BASE_MODEL_ID": "google/gemma-3-12b-it",
            "HF_MODEL_ID": destination_repo_id,
            "MODELNAME": model_name,
            "MODELTYPE": model_type,
            "MODELVERSIONTAG": source_revision,
            "NEW_MODELVERSIONTAG": destination_revision,
            "RANK": 127,
            "SEED": 42,
            "TRAIN_BATCH_SIZE": 8,
            "TRAIN_EPOCHS": 10,
            "TRAINING_QUEUE_JOBID": "",
            "TRAINING_QUEUE_JOBTYPE": ""
        }

        clearml_manager = ClearMLManager(activity_model)

        return await setup_clearml_task(
            clearml_manager=clearml_manager,
            clearml_project_name=f"dexit-{activity_model.tenant}/Entity Extraction",
            clearml_task_name=f"{model_name} - {destination_revision}",
            source_repo_id=source_repo_id,
            source_revision=source_revision,
            params=params
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
            payload_bytes = json.dumps(payload).encode('utf-8')

            # Upload to S3 using OpenDAL
            clearml_manager = ClearMLManager(activity_model)
            await s3_client.upload_object(
                path=clearml_manager.clearml_running_tasks_s3_path,
                file_name="running_tasks.json",
                content_type="application/json",
                file_content=payload_bytes
            )

            logger.success(f"Successfully stored ClearML task IDs at s3://{activity_model.storage_bucket_name}/{clearml_manager.clearml_running_tasks_s3_path}")

        except Exception as e:
            logger.error(f"Failed to store ClearML task IDs: {e}")
            raise