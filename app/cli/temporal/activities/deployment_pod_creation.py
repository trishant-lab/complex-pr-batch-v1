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
from kubernetes.dynamic.exceptions import NotFoundError
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


class KubernetesDeploymentUpdateActivityModel(LaunchpadCLIBaseModel):
    """
    KubernetesDeploymentUpdateActivityModel
    """

    namespace: str
    name: str

    docker_image: str | None = None
    volume_mounts: list | None = None
    volumes: list | None = None
    container_envs: list | None = None
    replicas: int | None = None


class KubernetesDeploymentUpdateActivity(Activity):
    """
    KubernetesDeploymentUpdateActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        get_timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        get_retry_policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=5), maximum_attempts=3)

    @staticmethod
    @activity.defn(name="KubernetesDeploymentUpdateActivity")
    async def defn(activity_model: KubernetesDeploymentUpdateActivityModel) -> None:
        """
        KubernetesDeploymentUpdateActivityModel
        """
        k8s_dynamic_client = get_dynamic_client()
        resource = get_resource(
            dynamic_client=k8s_dynamic_client,
            kind=ResourceKindEnum.Deployment,
            api_version=K8S_RESOURCE_VERSION,
        )

        try:
            log_info(
                f"Fetching existing deployment '{activity_model.name}' from namespace '{activity_model.namespace}'..."
            )
            existing_deployment_obj = resource.get(name=activity_model.name, namespace=activity_model.namespace)
        except NotFoundError:
            log_error(
                f"Deployment '{activity_model.name}' not found in namespace "
                f"'{activity_model.namespace}'. Cannot update."
            )
            raise

        deployment_as_dict = existing_deployment_obj.to_dict()

        if activity_model.volumes is not None:
            log_info("Updating volumes...")
            spec_volumes = deployment_as_dict["spec"]["template"]["spec"].setdefault("volumes", [])
            existing_volume_names = {vol["name"] for vol in spec_volumes}

            new_volumes_as_dicts = []
            for volume in activity_model.volumes:
                volume_name = volume["name"]
                if volume_name in existing_volume_names:
                    log_info(f"Volume '{volume_name}' already exists. Skipping.")
                    continue
                if volume.get("config_map_name"):
                    new_volumes_as_dicts.append(
                        {
                            "name": volume["name"],
                            "configMap": {
                                "name": volume["config_map_name"],
                                "items": [{"key": volume["key"], "path": volume["path"]}],
                            },
                        }
                    )
            spec_volumes.extend(new_volumes_as_dicts)

        if activity_model.volume_mounts is not None:
            log_info("Updating volume mounts...")
            container_mounts = deployment_as_dict["spec"]["template"]["spec"]["containers"][0].setdefault(
                "volumeMounts", []
            )
            existing_mount_names = {mount["name"] for mount in container_mounts}

            new_mounts_as_dicts = []
            for vm in activity_model.volume_mounts:
                mount_name = vm["name"]
                if mount_name in existing_mount_names:
                    log_info(f"Volume mount '{mount_name}' already exists. Skipping.")
                    continue

                mount_dict = {"name": vm["name"], "mountPath": vm["mount_path"]}
                if vm.get("sub_path"):
                    mount_dict["subPath"] = vm["sub_path"]
                if vm.get("read_only") is not None:
                    mount_dict["readOnly"] = vm["read_only"]
                new_mounts_as_dicts.append(mount_dict)
            container_mounts.extend(new_mounts_as_dicts)

        if activity_model.docker_image is not None:
            log_info(f"Updating docker image to '{activity_model.docker_image}'")
            deployment_as_dict["spec"]["template"]["spec"]["containers"][0]["image"] = activity_model.docker_image

        if "managedFields" in deployment_as_dict["metadata"]:
            del deployment_as_dict["metadata"]["managedFields"]

        payload = k8s_dynamic_client.client.sanitize_for_serialization(deployment_as_dict)

        try:
            log_info(f"Applying updated deployment '{activity_model.name}'")
            k8s_dynamic_client.server_side_apply(
                resource=resource,
                body=payload,
                field_manager="temporal-update-activity",
                force_conflicts=True,
            )
            log_info(f"Deployment '{activity_model.name}' updated successfully.")
        except Exception as e:
            log_error(f"Failed to apply updated deployment in namespace {activity_model.namespace}: {e!s}")
            raise
