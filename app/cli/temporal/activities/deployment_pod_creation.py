from datetime import timedelta

from kubernetes.client import (
    V1ConfigMapKeySelector,
    V1ConfigMapVolumeSource,
    V1Container,
    V1ContainerPort,
    V1Deployment,
    V1DeploymentSpec,
    V1EnvVar,
    V1EnvVarSource,
    V1KeyToPath,
    V1LocalObjectReference,
    V1ObjectMeta,
    V1PersistentVolumeClaimVolumeSource,
    V1PodSpec,
    V1PodTemplateSpec,
    V1ResourceRequirements,
    V1SecretKeySelector,
    V1SecurityContext,
    V1Volume,
    V1VolumeMount,
)
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.k8s_util import (
    ResourceKindEnum,
    get_dynamic_client,
    get_resource,
)
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_error, log_info

K8S_RESOURCE_VERSION = "apps/v1"


class KubernetesDeploymentActivityModel(LaunchpadCLIBaseModel):
    """
    KubernetesDeploymentActivityModel
    """

    namespace: str
    name: str
    docker_image: str
    request_resource: dict
    limit_resource: dict
    container_ports: dict[str, int]
    volume_mounts: list
    volumes: list
    container_envs: list
    replicas: int = 1
    container_command: list[str] | None = None
    container_args: list[str] | None = None
    init_containers: list | None = None


class KubernetesDeploymentActivity(Activity):
    """
    KubernetesDeploymentActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get Timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get Retry Policy
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="KubernetesDeploymentActivity")
    async def defn(activity_model: KubernetesDeploymentActivityModel) -> None:
        """
        KubernetesDeploymentActivityModel
        """
        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(
            dynamic_client=k8s_dynamic_client,
            kind=ResourceKindEnum.Deployment,
            api_version=K8S_RESOURCE_VERSION,
        )

        body = V1Deployment(
            api_version=K8S_RESOURCE_VERSION,
            kind=ResourceKindEnum.Deployment.value,
            metadata=V1ObjectMeta(namespace=activity_model.namespace, name=activity_model.name),
            spec=V1DeploymentSpec(
                replicas=activity_model.replicas,
                selector={"matchLabels": {"app": activity_model.name}},
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(labels={"app": activity_model.name}),
                    spec=V1PodSpec(
                        node_selector={"app": "314e"},
                        image_pull_secrets=[V1LocalObjectReference(name="registrycred")],
                        scheduler_name="volcano",
                        init_containers=[
                            V1Container(
                                name=init_container["name"],
                                image=init_container["image"],
                                command=init_container["command"],
                                args=init_container["args"],
                            )
                            for init_container in activity_model.init_containers or []
                        ],
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
        try:
            k8s_dynamic_client.server_side_apply(
                resource=resource,
                body=payload,
                field_manager="kubectl-client-side-apply",
                force_conflicts=True,
            )
            log_info(f"Deployment created in namespace {activity_model.namespace}")
        except Exception as e:
            log_error(f"Failed to create Deployment in namespace {activity_model.namespace}: {e!s}")
            raise
