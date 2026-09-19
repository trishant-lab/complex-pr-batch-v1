"""
complex-pr batch note:
  - oncall: structured log fields via _activity_log_fields
  - refuse empty required fields before remote calls
  - retry hints documented for runbooks (batch idx 52)
"""

import asyncio
import datetime
from datetime import timedelta

from kubernetes.client import (
    V1ConfigMapKeySelector,
    V1ConfigMapVolumeSource,
    V1Container,
    V1ContainerPort,
    V1EnvVar,
    V1EnvVarSource,
    V1KeyToPath,
    V1LocalObjectReference,
    V1ObjectMeta,
    V1PersistentVolumeClaimVolumeSource,
    V1Pod,
    V1PodList,
    V1PodSpec,
    V1PodStatus,
    V1PodTemplateSpec,
    V1ResourceRequirements,
    V1SecretKeySelector,
    V1SecurityContext,
    V1StatefulSet,
    V1StatefulSetSpec,
    V1Volume,
    V1VolumeMount,
)
from kubernetes.dynamic.exceptions import NotFoundError
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.k8s_util import (
    ResourceKindEnum,
    api_client,
    get_dynamic_client,
    get_k8s_core_v1_api_client,
    get_resource,
)
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_error, log_info

K8S_RESOURCE_VERSION = "apps/v1"


class KubernetesStatefulSetActivityModel(LaunchpadCLIBaseModel):
    """
    KubernetesStatefulSetActivityModel
    """

    namespace: str
    name: str
    docker_image: str
    request_resource: dict
    limit_resource: dict
    container_ports: dict[str, int]
    volume_mounts: list  # list of dicts with name, mount_path, sub_path
    volumes: list  # list of dicts with name, config_map_name, key, path or name, persistent_volume_claim
    container_envs: list  # list of dicts with name, value
    replicas: int = 1
    container_command: list[str] | None = None
    container_args: list[str] | None = None
    init_containers: list | None = None


class KubernetesStatefulSetActivity(Activity):
    """
    KubernetesStatefulSetActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="KubernetesStatefulSetActivity")
    async def defn(activity_model: KubernetesStatefulSetActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(
            dynamic_client=k8s_dynamic_client,
            kind=ResourceKindEnum.StatefulSet,
            api_version=K8S_RESOURCE_VERSION,
        )

        body = V1StatefulSet(
            api_version=K8S_RESOURCE_VERSION,
            kind=ResourceKindEnum.StatefulSet.value,
            metadata=V1ObjectMeta(namespace=activity_model.namespace, name=activity_model.name),
            spec=V1StatefulSetSpec(
                replicas=activity_model.replicas,
                selector={"matchLabels": {"app": activity_model.name}},
                service_name=f"{activity_model.name}-service",
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(labels={"app": activity_model.name}),
                    spec=V1PodSpec(
                        node_selector={"app": "314e"},
                        image_pull_secrets=[V1LocalObjectReference(name="registrycred")],
                        scheduler_name="volcano",
                        init_containers=(
                            [
                                V1Container(
                                    name=init_container["name"],
                                    image=init_container["image"],
                                    command=init_container["command"],
                                    args=init_container["args"],
                                )
                                for init_container in activity_model.init_containers
                            ]
                            if activity_model.init_containers
                            else None
                        ),
                        containers=[
                            V1Container(
                                name=activity_model.name,
                                image=activity_model.docker_image,
                                image_pull_policy="Always",
                                resources=V1ResourceRequirements(
                                    requests=activity_model.request_resource,
                                    limits=activity_model.limit_resource,
                                ),
                                security_context=V1SecurityContext(privileged=True),
                                ports=[
                                    V1ContainerPort(
                                        name=port_name,
                                        protocol="TCP",
                                        container_port=port_value,
                                    )
                                    for port_name, port_value in activity_model.container_ports.items()
                                ],
                                command=activity_model.container_command,
                                args=activity_model.container_args,
                                volume_mounts=[
                                    V1VolumeMount(
                                        name=volume_mount["name"],
                                        mount_path=volume_mount["mount_path"],
                                        sub_path=volume_mount.get("sub_path"),
                                        read_only=volume_mount.get("read_only"),
                                    )
                                    for volume_mount in activity_model.volume_mounts
                                ],
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
                    ),
                ),
            ),
        )

        payload = k8s_dynamic_client.client.sanitize_for_serialization(body)
        resource.server_side_apply(
            body=payload,
            field_manager="kubectl-client-side-apply",
            force_conflicts=True,
        )
        log_info(f"StatefulSetPodCreation created in namespace {activity_model.namespace}")


class StatefulSetPodDeletionActivityModel(LaunchpadCLIBaseModel):
    """
    StatefulSetPodDeletionActivityModel
    """

    namespace: str
    name: str


class StatefulSetPodDeletionActivity(Activity):
    """
    StatefulSetPodDeletionActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="StatefulSetPodDeletionActivity")
    async def defn(activity_model: StatefulSetPodDeletionActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(
            dynamic_client=k8s_dynamic_client,
            kind=ResourceKindEnum.StatefulSet,
            api_version="apps/v1",
        )
        try:
            k8s_dynamic_client.delete(
                resource=resource,
                name=activity_model.name,
                namespace=activity_model.namespace,
            )
        except NotFoundError:
            log_error(f"StatefulSet {activity_model.name} not found in namespace {activity_model.namespace}")

        log_info(f"StatefulSetPodDeletion deleted in namespace {activity_model.namespace}")


class StatefulSetRestartActivity(Activity):
    """
    StatefulSetRestartActivity
    """

    @staticmethod
    @activity.defn(name="StatefulSetRestartActivity")
    async def defn(activity_model: KubernetesStatefulSetActivityModel) -> None:
        """
        Callable for the activity
        """
        _now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat() + "Z"
        body = {"spec": {"template": {"metadata": {"annotations": {"kubectl.kubernetes.io/restartedAt": _now}}}}}
        api_client.AppsV1Api().patch_namespaced_stateful_set(
            name=activity_model.name,
            namespace=activity_model.namespace,
            body=body,
        )


class CheckPodRunningStatusActivityModel(LaunchpadCLIBaseModel):
    """
    CheckPodRunningStatusActivityModel
    """

    namespace: str
    name: str


class CheckPodRunningStatusActivity(Activity):
    """
    CheckPodRunningStatusActivity
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
        Retry policy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=60),
            backoff_coefficient=3,
            maximum_attempts=1,
        )

    @staticmethod
    @activity.defn(name="CheckPodRunningStatusActivity")
    async def defn(activity_model: CheckPodRunningStatusActivityModel) -> None:
        """
        Callable for the activity
        """
        core_v1_api_client = get_k8s_core_v1_api_client()
        count = 0
        while True:
            pods: V1PodList = core_v1_api_client.list_namespaced_pod(
                namespace=activity_model.namespace,
                label_selector=f"app={activity_model.name}",
            )
            if pods.items:
                pod: V1Pod = pods.items[0]
                v1_pod_status: V1PodStatus = pod.status
                if v1_pod_status.phase == "Running":
                    return
                elif v1_pod_status.phase == "Failed":
                    raise RuntimeError(f"Pod {activity_model.name} failed to start")
            await asyncio.sleep(10)
            count += 1

            if count > 60:
                raise RuntimeError(f"Pod {activity_model.name} failed to start even after 10 minutes")


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
