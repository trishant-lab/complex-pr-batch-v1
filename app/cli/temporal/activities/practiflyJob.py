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
    CoreV1Api,
    V1Pod,
    V1PodList,
    V1JobStatus,
)
from kubernetes.dynamic import DynamicClient, Resource

from app.cli.k8s_util import ResourceKindEnum, get_dynamic_client, get_resource
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info, log_error
from app.core.settings import AppSettings, get_settings


async def check_logs(namespace: str, job_name: str, job_type: str) -> bool:
    """
    Check logs
    """
    expected_msg = (
        f"{namespace.strip().lower()} Alembic run succeeded!"
        if job_type.lower() == "alembic"
        else f"{namespace.strip().lower()} Provisioning succeeded!"
    )

    try:
        pod_resource = get_resource(dynamic_client=get_dynamic_client(), kind=ResourceKindEnum.Pod, api_version="v1")

        pods: V1PodList = pod_resource.get(
            namespace=namespace,
            kind=ResourceKindEnum.Pod.value,
            label_selector=f"job-name={job_name}",
            field_selector="status.phase=Succeeded",
        )

        if not pods.items:
            log_info(f"Pod not found for job {job_name} in namespace {namespace}")
            return False

        # Get newest pod
        pod: V1Pod = sorted(pods.items, key=lambda x: x.metadata.creation_timestamp, reverse=True)[0]
        log_info(f"Selected pod: {pod.metadata.name}")

        core_v1_api = CoreV1Api()
        logs = core_v1_api.read_namespaced_pod_log(name=pod.metadata.name, namespace=namespace)

        if expected_msg not in logs.lower():
            log_error(f"{namespace}: {logs}")
            return False
        return True

    except Exception as e:
        log_error(f"Error checking logs: {e}")
        return False


async def wait_for_job_to_complete(namespace: str, job_name: str, job_type: str) -> bool:
    """
    Wait for job to complete
    """
    check_interval = 10  # seconds
    max_iterations = 60  # 60 iterations * 10 seconds = 600 seconds (10 minutes)
    iteration = 0

    job_resource = get_resource(dynamic_client=get_dynamic_client(), kind=ResourceKindEnum.Job, api_version="v1")

    try:
        while True:
            log_info(f"Checking Job status periodically for {namespace}")
            job: V1Job = job_resource.get(namespace=namespace, name=job_name)
            job_status: V1JobStatus = job.status

            if job_status and job_status.completion_time:
                log_info(f"Job {job_name} completed for {namespace}")
                return check_logs(namespace=namespace, job_name=job_name, job_type=job_type)

            elif iteration == max_iterations:
                log_error(f"Number of retry exited job {job_name} for {namespace}: 10 minutes")
                raise Exception(f"Number of retry exited job {job_name} for {namespace}: 10 minutes")

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
    job_name: str
    job_type: str
    image_tag: str
    argument: str


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

        resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Job, api_version="v1")

        body = V1Job(
            api_version="batch/v1",
            kind=ResourceKindEnum.Job.value,
            metadata=V1ObjectMeta(
                namespace=activity_model.tenant,
                name=activity_model.job_name,
                labels={"app": "practifly", "jobKind": activity_model.job_type},
                annotations={"app": "practifly", "jobKind": activity_model.job_type},
            ),
            spec=V1JobSpec(
                template=V1JobTemplateSpec(
                    spec=V1PodSpec(
                        node_selector={"app": "314e"},
                        image_pull_secrets=[V1LocalObjectReference(name="registrycred")],
                        containers=[
                            V1Container(
                                name=activity_model.job_name,
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
                                args=[activity_model.argument],
                            )
                        ],
                        volumes=[
                            V1Volume(
                                name="practifly-provisioning-config",
                                config_map=V1ConfigMapVolumeSource(
                                    name="practifly-provisioning-config",
                                    items=[
                                        V1KeyToPath(key="provisioning-config.json", path="provisioning-config.json"),
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

        delete(k8s_dynamic_client, resource, activity_model.job_name, activity_model.tenant)

        k8s_dynamic_client.server_side_apply(
            resource=resource, body=payload, field_manager="kubectl-client-side-apply", force_conflicts=True
        )

        status = await wait_for_job_to_complete(
            namespace=activity_model.tenant,
            job_name=activity_model.job_name,
            job_type=activity_model.job_type,
        )

        log_info(f"Job {activity_model.job_name} created successfully")

        if not status:
            log_error(f"Job {activity_model.job_name} failed for {activity_model.tenant}")
            raise Exception(f"Job {activity_model.job_name} failed for {activity_model.tenant}")

        log_info(f"Job {activity_model.job_name} completed successfully for {activity_model.tenant}")


def delete(k8s_dynamic_client: DynamicClient, resource: Resource, job_name: str, namespace: str) -> None:
    """
    Delete method
    """
    try:
        k8s_dynamic_client.delete(resource=resource, name=job_name, namespace=namespace)
    except NotFoundError:
        log_error(f"{job_name} job not found for {namespace}")


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

        delete(k8s_dynamic_client, resource, activity_model.job_name, activity_model.namespace)
