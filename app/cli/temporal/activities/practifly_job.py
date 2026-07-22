import asyncio
from datetime import timedelta

import kubernetes as k8s
from kubernetes.client import (
    BatchV1Api,
    V1ConfigMapVolumeSource,
    V1Container,
    V1DeleteOptions,
    V1EnvVar,
    V1EnvVarSource,
    V1Job,
    V1JobSpec,
    V1JobStatus,
    V1JobTemplateSpec,
    V1KeyToPath,
    V1LocalObjectReference,
    V1ObjectMeta,
    V1PodSpec,
    V1SecretKeySelector,
    V1Volume,
    V1VolumeMount,
)
from kubernetes.dynamic import Resource
from kubernetes.dynamic.exceptions import NotFoundError
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.k8s_util import ResourceKindEnum, get_dynamic_client, get_k8s_core_v1_api_client, get_resource
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_error, log_info
from app.cli.temporal.practifly.models.practifly_spec import PractiflyJobEnum
from app.core.settings import AppSettings, get_settings

JOB_BACKOFF_LIMIT = 3


def check_pod_logs(namespace: str, job_name: str, job_type: PractiflyJobEnum) -> bool:
    """
    Check pod logs, return True if the logs contain the expected logs
    """
    k8s_api_client = get_k8s_core_v1_api_client()
    pods: k8s.client.V1PodList = k8s_api_client.list_namespaced_pod(
        namespace=namespace,
        label_selector=f"job-name={job_name}",
    )
    if len(pods.items) == 0:
        msg = f"No pod found for job {job_name} in namespace {namespace}"
        log_error(msg)
        raise RuntimeError(msg)

    pod: k8s.client.V1Pod = sorted(pods.items, key=lambda x: x.metadata.creation_timestamp, reverse=True)[0]
    # parse the logs
    logs = k8s_api_client.read_namespaced_pod_log(name=pod.metadata.name, namespace=namespace)
    expected_logs = PractiflyJobEnum.get_expected_log_messages(job_type)
    if any(expected_log.format(namespace=namespace) in logs for expected_log in expected_logs):
        return True
    msg = f"Job failed for tenant {namespace}"
    log_error(f"Logs: {logs}")
    raise RuntimeError(msg)


async def poll_job_status(job_resource: Resource, namespace: str, job_name: str, job_type: PractiflyJobEnum) -> bool:
    """
    Wait for job to complete
    """
    check_interval = 10  # seconds
    max_iterations = 90  # 90 iterations * 10 seconds = 900 seconds (15 minutes)
    iteration = 0

    while iteration < max_iterations:
        try:
            job: V1Job = job_resource.get(name=job_name, namespace=namespace)
            job_status: V1JobStatus = job.status

            if job_status.failed and job_status.failed >= JOB_BACKOFF_LIMIT:
                check_pod_logs(namespace, job_name, job_type)
                msg = f"Job failed for tenant {namespace}: {job_status!r}"
                log_error(msg)
                raise RuntimeError(msg)

            if job_status.completionTime is not None:
                if job_status.succeeded < 1:
                    msg = f"Job failed for tenant {namespace}: {job_status!r}"
                    log_error(msg)
                    raise RuntimeError(msg)
                check_pod_logs(namespace, job_name, job_type)
                return True
        except k8s.client.ApiException as e:
            if e.status != 404:
                raise
        await asyncio.sleep(check_interval)
        iteration += 1
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
        return timedelta(seconds=300)

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
    @activity.defn(name="PractiflyJobActivity")
    async def defn(activity_model: PractiflyJobActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()
        k8s_api_client = get_k8s_core_v1_api_client()
        config: AppSettings = get_settings()

        job_name = PractiflyJobEnum.get_job_name(activity_model.job_type)
        argument = PractiflyJobEnum.get_argument(activity_model.job_type)

        job_resource = get_resource(
            dynamic_client=k8s_dynamic_client,
            kind=ResourceKindEnum.Job,
            api_version="batch/v1",
        )

        job: V1Job | None = None
        try:
            job = job_resource.get(name=job_name, namespace=activity_model.tenant)
        except k8s.client.ApiException as e:
            if e.status != 404:
                raise

        if job is not None:
            k8s_api_client.delete_collection_namespaced_pod(
                namespace=activity_model.tenant,
                label_selector=f"job-name={job_name}",
                grace_period_seconds=0,
                timeout_seconds=120,
            )
            job_resource.delete(
                name=job_name,
                namespace=activity_model.tenant,
                grace_period_seconds=0,
            )

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
                backoff_limit=JOB_BACKOFF_LIMIT,
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

        k8s_dynamic_client.server_side_apply(
            resource=job_resource,
            body=payload,
            field_manager="kubectl-client-side-apply",
            force_conflicts=True,
        )

        log_info(f"Job {job_name} created successfully for {activity_model.tenant}")

        await poll_job_status(
            job_resource=job_resource,
            namespace=activity_model.tenant,
            job_name=job_name,
            job_type=activity_model.job_type,
        )
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
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="DeleteJobActivity")
    async def defn(activity_model: DeleteJobActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Job, api_version="v1")

        delete(resource=resource, job_name=activity_model.job_name, namespace=activity_model.namespace)
