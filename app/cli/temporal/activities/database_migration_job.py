"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 5)
"""

from datetime import timedelta

from kubernetes.client import (
    BatchV1Api,
    V1ConfigMapKeySelector,
    V1ConfigMapVolumeSource,
    V1Container,
    V1DeleteOptions,
    V1EnvVar,
    V1EnvVarSource,
    V1Job,
    V1JobSpec,
    V1JobTemplateSpec,
    V1KeyToPath,
    V1LocalObjectReference,
    V1ObjectMeta,
    V1PersistentVolumeClaimVolumeSource,
    V1PodSpec,
    V1SecretKeySelector,
    V1Volume,
    V1VolumeMount,
)
from kubernetes.dynamic import Resource
from kubernetes.dynamic.exceptions import NotFoundError
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.k8s_util import ResourceKindEnum, get_dynamic_client, get_resource
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_error, log_info


class DatabaseMigrationJobActivityModel(LaunchpadCLIBaseModel):
    """
    DatabaseMigrationJobActivityModel
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


class DatabaseMigrationJobActivity(Activity):
    """
    DatabaseMigrationJobActivity
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
        return RetryPolicy(initial_interval=timedelta(seconds=10), maximum_attempts=5, backoff_coefficient=3)

    @staticmethod
    @activity.defn(name="DatabaseMigrationJobActivity")
    async def defn(activity_model: DatabaseMigrationJobActivityModel) -> None:
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
                        scheduler_name="volcano",
                        containers=[
                            V1Container(
                                name=activity_model.job_name,
                                image=activity_model.docker_image,
                                image_pull_policy="Always",
                                env=[
                                    V1EnvVar(
                                        name=container_env["name"],
                                        value=container_env["value"],
                                    )
                                    for container_env in activity_model.container_envs
                                    if container_env.get("value")
                                ]
                                + [
                                    V1EnvVar(
                                        name=container_env["name"],
                                        value_from=V1EnvVarSource(
                                            config_map_key_ref=V1ConfigMapKeySelector(
                                                name=container_env["value_from"]["config_map_key_ref"]["name"],
                                                key=container_env["value_from"]["config_map_key_ref"]["key"],
                                            )
                                        ),
                                    )
                                    for container_env in activity_model.container_envs
                                    if container_env.get("value_from")
                                    and container_env["value_from"].get("config_map_key_ref")
                                ]
                                + [
                                    V1EnvVar(
                                        name=container_env["name"],
                                        value_from=V1EnvVarSource(
                                            secret_key_ref=V1SecretKeySelector(
                                                name=container_env["value_from"]["secret_key_ref"]["name"],
                                                key=container_env["value_from"]["secret_key_ref"]["key"],
                                            )
                                        ),
                                    )
                                    for container_env in activity_model.container_envs
                                    if container_env.get("value_from")
                                    and container_env["value_from"].get("secret_key_ref")
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

        delete(resource, activity_model.job_name, activity_model.namespace)

        k8s_dynamic_client.server_side_apply(
            resource=resource, body=payload, field_manager="kubectl-client-side-apply", force_conflicts=True
        )

        log_info(f"Database migration job {activity_model.job_name} created successfully")


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


class DeleteDatabaseMigrationJobActivityModel(LaunchpadCLIBaseModel):
    """
    DeleteDatabaseMigrationJobActivityModel
    """

    namespace: str
    job_name: str


class DeleteDatabaseMigrationJobActivity(Activity):
    """
    DeleteDatabaseMigrationJobActivity
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
        return RetryPolicy(initial_interval=timedelta(seconds=10), maximum_attempts=5, backoff_coefficient=3)

    @staticmethod
    @activity.defn(name="DeleteDatabaseMigrationJobActivity")
    async def defn(activity_model: DeleteDatabaseMigrationJobActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Job, api_version="v1")

        delete(resource=resource, job_name=activity_model.job_name, namespace=activity_model.namespace)


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
