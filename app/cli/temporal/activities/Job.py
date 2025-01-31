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
    V1PersistentVolumeClaimVolumeSource,
    V1EnvVar,
    V1DeleteOptions,
    BatchV1Api,
)
from kubernetes.dynamic import Resource

from app.cli.k8s_util import ResourceKindEnum, get_dynamic_client, get_resource
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info, log_error


class JobActivityModel(LaunchpadCLIBaseModel):
    """
    JobActivityModel
    """

    namespace: str
    job_name: str
    docker_image: str
    volume_mounts: list[
        dict
    ]  # [{"name": "tenant-volume", "mount_path": "/config/tenant-config.json", "sub_path": "tenant-config.json"},]
    volumes: list[dict]  # [{"name": "tenant-volume", "config_map_name":
    # "jeeves-tenant-config", "key": "tenant-config.json", "path": "tenant-config.json"},]
    container_envs: list[dict]  # [{"name": "APP_CONFIG_FILE", "value": "/config/tenant-config.json"},]
    argument: str
    job_type: str
    product: str


class JobActivity(Activity):
    """
    JobActivity
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
        return RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=3, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="JobActivity")
    async def defn(activity_model: JobActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Job, api_version="v1")

        body = V1Job(
            api_version="batch/v1",
            kind=ResourceKindEnum.Job.value,
            metadata=V1ObjectMeta(
                namespace=activity_model.namespace,
                name=activity_model.job_name,
                labels={"app": activity_model.product.lower(), "jobKind": activity_model.job_type},
                annotations={"app": activity_model.product.lower(), "jobKind": activity_model.job_type},
            ),
            spec=V1JobSpec(
                template=V1JobTemplateSpec(
                    spec=V1PodSpec(
                        node_selector={"app": "314e"},
                        image_pull_secrets=[V1LocalObjectReference(name="registrycred")],
                        containers=[
                            V1Container(
                                name=activity_model.job_name,
                                image=activity_model.docker_image,
                                image_pull_policy="Always",
                                env=[
                                    V1EnvVar(name=container_env["name"], value=container_env["value"])
                                    for container_env in activity_model.container_envs
                                ],
                                volume_mounts=[
                                    V1VolumeMount(
                                        name=volume_mount["name"],
                                        mount_path=volume_mount["mount_path"],
                                        sub_path=volume_mount.get("sub_path"),
                                        read_only=volume_mount.get("read_only"),
                                    )
                                    for volume_mount in activity_model.volume_mounts
                                ],
                                command=["/bin/sh", "-c"],
                                args=[activity_model.argument],
                            )
                        ],
                        volumes=[
                            V1Volume(
                                name=volume["name"],
                                config_map=V1ConfigMapVolumeSource(
                                    name=volume["config_map_name"],
                                    items=[V1KeyToPath(key=volume["key"], path=volume["path"])],
                                ),
                            )
                            for volume in activity_model.volumes
                            if volume.get("config_map_name")
                        ]
                        + [
                            V1Volume(
                                name=volume["name"],
                                persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(
                                    claim_name=volume["persistent_volume_claim"]
                                ),
                            )
                            for volume in activity_model.volumes
                            if volume.get("persistent_volume_claim")
                        ],
                        restart_policy="Never",
                    )
                ),
            ),
        )

        payload = k8s_dynamic_client.client.sanitize_for_serialization(body)

        delete(resource=resource, job_name=activity_model.job_name, namespace=activity_model.namespace)

        k8s_dynamic_client.server_side_apply(
            resource=resource, body=payload, field_manager="kubectl-client-side-apply", force_conflicts=True
        )

        log_info(f"Job {activity_model.job_name} created successfully")


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
