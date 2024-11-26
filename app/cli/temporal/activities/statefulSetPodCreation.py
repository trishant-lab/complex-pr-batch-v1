from temporalio import activity, workflow
from temporalio.common import RetryPolicy


with workflow.unsafe.imports_passed_through():
    from datetime import timedelta
    from kubernetes.client import (
        V1StatefulSet,
        V1ObjectMeta,
        V1StatefulSetSpec,
        V1PodTemplateSpec,
        V1PodSpec,
        V1Container,
        V1ContainerPort,
        V1Volume,
        V1VolumeMount,
        V1ResourceRequirements,
        V1SecurityContext,
        V1ConfigMapVolumeSource,
        V1KeyToPath,
        V1PersistentVolumeClaimVolumeSource,
        V1EnvVar,
        V1LocalObjectReference,
        V1ConfigMapKeySelector,
        V1EnvVarSource,
    )

    from app.cli.k8s_util import ResourceKindEnum, get_dynamic_client, get_resource
    from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
    from app.cli.temporal.core.log import log_info


class KubernetesStatefulSetActivityModel(LaunchpadCLIBaseModel):
    """
    KubernetesStatefulSetActivityModel
    """

    namespace: str
    name: str
    docker_image: str
    request_resource: dict
    limit_resource: dict
    container_ports: list[int]
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
        return RetryPolicy(initial_interval=timedelta(seconds=1), backoff_coefficient=2, maximum_attempts=5)

    @staticmethod
    @activity.defn(name="KubernetesStatefulSetActivity")
    async def defn(activity_model: KubernetesStatefulSetActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(
            dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.StatefulSet, api_version="apps/v1"
        )

        container_port_name = "http" if len(activity_model.container_port) <=1 else ""

        body = V1StatefulSet(
            api_version="apps/v1",
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
                        init_containers=[
                            V1Container(
                                name=init_container["name"],
                                image=init_container["image"],
                                command=init_container["command"],
                                args=init_container["args"],
                            )
                            for init_container in activity_model.init_containers
                        ]
                        if activity_model.init_containers
                        else None,
                        containers=[
                            V1Container(
                                name=activity_model.name,
                                image=activity_model.docker_image,
                                image_pull_policy="Always",
                                resources=V1ResourceRequirements(
                                    requests=activity_model.request_resource, limits=activity_model.limit_resource
                                ),
                                security_context=V1SecurityContext(privileged=True),
                                ports=[
                                    V1ContainerPort(
                                        name=container_port_name if container_port_name else f"http-{container_port}", protocol="TCP", container_port=container_port
                                    )
                                    for container_port in activity_model.container_ports
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
                                    V1EnvVar(name=container_env["name"], value=container_env["value"])
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
        resource.server_side_apply(body=payload, field_manager="kubectl-client-side-apply", force_conflicts=True)
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
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5, backoff_coefficient=2)

    @staticmethod
    @activity.defn(name="StatefulSetPodDeletionActivity")
    async def defn(activity_model: StatefulSetPodDeletionActivityModel) -> None:
        """
        Callable for the activity
        """
        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(
            dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.StatefulSet, api_version="apps/v1"
        )

        k8s_dynamic_client.delete(resource=resource, name=activity_model.name, namespace=activity_model.namespace)

        log_info(f"StatefulSetPodDeletion deleted in namespace {activity_model.namespace}")
