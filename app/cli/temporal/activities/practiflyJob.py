import asyncio
from temporalio import activity
from temporalio.common import RetryPolicy
from kubernetes.dynamic.exceptions import NotFoundError

from datetime import timedelta
from kubernetes.client import (
    V1Job,
    V1ObjectMeta,
    V1JobSpec,
    V1JobTemplateSpec,
    V1PodSpec,
    V1LocalObjectReference,
    V1Container,
    V1VolumeMount,
    V1Volume,
    V1ConfigMapVolumeSource,
    V1KeyToPath,
    V1EnvVar,
    V1EnvVarSource,
    V1SecretKeySelector,
    V1Pod,
    V1PodList,
    V1JobStatus,
    V1DeleteOptions,
    BatchV1Api,
)
from kubernetes.dynamic import Resource
from app.cli.k8s_util import ResourceKindEnum, get_dynamic_client, get_k8s_core_v1_api_client, get_resource
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info, log_error
from app.cli.temporal.practifly.models.practiflySpec import PractiflyJobEnum
from app.core.settings import AppSettings, get_settings


async def check_logs(namespace: str, job_name: str, expected_log_message: str) -> bool:
    """
    Check logs
    """
    try:
        core_v1_api = get_k8s_core_v1_api_client()

        pods: V1PodList = core_v1_api.list_namespaced_pod(namespace=namespace, label_selector=f"job-name={job_name}")

        if not pods.items:
            log_info(f"Pod not found for job {job_name} in namespace {namespace}")
            return False

        # Get newest pod
        pod: V1Pod = sorted(pods.items, key=lambda x: x.metadata.creation_timestamp, reverse=True)[0]
        log_info(f"Selected pod: {pod.metadata.name}")

        logs = core_v1_api.read_namespaced_pod_log(name=pod.metadata.name, namespace=namespace)

        if expected_log_message not in logs.lower():
            log_error(f"{namespace}: {logs}")
            return False
        return True

    except Exception as e:
        log_error(f"Error checking logs: {e}")
        return False


async def check_execution_status(resource: Resource, namespace: str, job_name: str, expected_log_message: str) -> bool:
    """
    Wait for job to complete
    """
    check_interval = 10  # seconds
    max_iterations = 60  # 60 iterations * 10 seconds = 600 seconds (10 minutes)
    iteration = 0

    try:
        while True:
            log_info(f"Checking Job status periodically for {namespace}")
            job: V1Job = resource.get(namespace=namespace, name=job_name)
            job_status: V1JobStatus = job.status

            if job_status and job_status.completion_time:
                log_info(f"Job {job_name} completed for {namespace}")
                return check_logs(
                    namespace=namespace,
                    job_name=job_name,
                    expected_log_message=expected_log_message,
                )

            elif iteration == max_iterations:
                log_error(f"Number of retry exited job {job_name} for {namespace}: 10 minutes")
                raise TimeoutError(f"Number of retry exited job {job_name} for {namespace}: 10 minutes")

            log_info(f"Job {job_name} not completed yet for {namespace}")
            # Sleep for 10 seconds
            await asyncio.sleep(check_interval)
            iteration += 1
    except NotFoundError:
        log_error(f"Job {job_name} not found for {namespace}")
        return False


class PractiflyJobActivityModel(LaunchpadCLIBaseModel):
    """
    PractiflyJobActivityModel
    """

    tenant: str
    image_tag: str
    job_type: PractiflyJobEnum


class PractiflyJobActivity(Activity):
    """
    PractiflyJobActivity
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
    @activity.defn(name="PractiflyJobActivity")
    async def defn(activity_model: PractiflyJobActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()
        config: AppSettings = get_settings()

        job_name = PractiflyJobEnum.get_job_name(activity_model.job_type)
        argument = PractiflyJobEnum.get_argument(activity_model.job_type)
        expected_log_message = PractiflyJobEnum.get_expected_log_message(activity_model.job_type)

        resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Job, api_version="v1")

        # Get the job
        job: V1Job = resource.get(namespace=activity_model.tenant, name=job_name)

        if activity_model.job_type == PractiflyJobEnum.PROVISIONING and job is not None:
            log_info(f"Job {job_name} already exists for {activity_model.tenant}")
        else:
            delete(resource=resource, job_name=job_name, namespace=activity_model.tenant)
            body = V1Job(
                api_version="batch/v1",
                kind=ResourceKindEnum.Job.value,
                metadata=V1ObjectMeta(
                    namespace=activity_model.tenant,
                    name=job_name,
                    labels={"app": "practifly", "jobKind": activity_model.job_type.value},
                    annotations={"app": "practifly", "jobKind": activity_model.job_type.value},
                ),
                spec=V1JobSpec(
                    template=V1JobTemplateSpec(
                        spec=V1PodSpec(
                            node_selector={"app": "314e"},
                            image_pull_secrets=[V1LocalObjectReference(name="registrycred")],
                            containers=[
                                V1Container(
                                    name=job_name,
                                    image=f"registry.314ecorp.tech/practifly-server:{activity_model.image_tag}",
                                    image_pull_policy="Always",
                                    env=[
                                        V1EnvVar(name="DEPLOYMENT", value=config.env),
                                        V1EnvVar(
                                            name="POSTGRES__PASSWORD",
                                            value_from=V1EnvVarSource(
                                                secret_key_ref=V1SecretKeySelector(
                                                    name="practifly-postgres", key="password"
                                                )
                                            ),
                                        ),
                                        V1EnvVar(
                                            name="POSTGRES__USER",
                                            value=f"practifly_{activity_model.tenant}",
                                        ),
                                        V1EnvVar(
                                            name="RELEASE_VERSION",
                                            value=activity_model.image_tag,
                                        ),
                                        V1EnvVar(
                                            name="PROVISIONING_CONFIG",
                                            value="/provisioningConfig/provisioning-config.json",
                                        ),
                                    ],
                                    volume_mounts=[
                                        V1VolumeMount(
                                            name="practifly-provisioning-config",
                                            mount_path="/provisioningConfig",
                                            read_only=True,
                                        )
                                    ],
                                    command=["/bin/sh", "-c"],
                                    args=[argument],
                                )
                            ],
                            volumes=[
                                V1Volume(
                                    name="practifly-provisioning-config",
                                    config_map=V1ConfigMapVolumeSource(
                                        name="practifly-provisioning-config",
                                        items=[
                                            V1KeyToPath(
                                                key="provisioning-config.json", path="provisioning-config.json"
                                            ),
                                        ],
                                    ),
                                )
                            ],
                            restart_policy="Never",
                        )
                    ),
                ),
            )

            payload = k8s_dynamic_client.client.sanitize_for_serialization(body)

            k8s_dynamic_client.server_side_apply(
                resource=resource, body=payload, field_manager="kubectl-client-side-apply", force_conflicts=True
            )

            log_info(f"Job {job_name} created successfully for {activity_model.tenant}")

        status = await check_execution_status(
            resource=resource,
            namespace=activity_model.tenant,
            job_name=job_name,
            expected_log_message=expected_log_message,
        )

        if not status:
            log_error(f"Job {job_name} failed for {activity_model.tenant}")
            raise RuntimeError(f"Job {job_name} failed for {activity_model.tenant}")

        log_info(f"Job {job_name} completed successfully for {activity_model.tenant}")


def delete(resource: Resource, job_name: str, namespace: str) -> None:
    """
    Delete method
    """
    # First check if the job exists
    try:
        resource.get(name=job_name, namespace=namespace)
        log_info(f"Found existing job {job_name} in namespace {namespace}")
    except NotFoundError:
        log_info(f"No existing job {job_name} found in namespace {namespace}")
        return

    try:
        # Delete the job with propagation policy to clean up dependent objects
        delete_options = V1DeleteOptions(propagation_policy="Foreground")
        batch_v1 = BatchV1Api()
        batch_v1.delete_namespaced_job(name=job_name, namespace=namespace, body=delete_options)
        log_info(f"Successfully deleted job {job_name} in namespace {namespace}")
    except Exception as e:
        log_error(f"Error during deletion of job {job_name}: {e}")


class DeleteJobActivityModel(LaunchpadCLIBaseModel):
    """
    DeleteJobActivityModel
    """

    namespace: str
    job_name: str


class DeleteJobActivity(Activity):
    """
    DeleteJobActivity
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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5, backoff_coefficient=2)

    @staticmethod
    @activity.defn(name="DeleteJobActivity")
    async def defn(activity_model: DeleteJobActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Job, api_version="v1")

        delete(resource=resource, job_name=activity_model.job_name, namespace=activity_model.namespace)
