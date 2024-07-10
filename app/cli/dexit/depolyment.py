from app.cli.temporal.core.log import log_info
from kubernetes import client as k8s_client
from kubernetes.client import V1PersistentVolumeClaimVolumeSource
from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.dexit.dexit import ProductName
from app.cli.dexit.dexit import DexitSpec
from app.core.settings import get_settings, AppSettings


class DeploymentServer(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self: "DeploymentServer", dexit: DexitSpec) -> None:
        """
        Initialize DeploymentServer
        """
        self.dexit: DexitSpec = dexit
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Deployment, api_version="apps/v1"
        )
        self.config: AppSettings = get_settings()

        self.postgres_user = f"dexit_{dexit.tenant}"
        self.env: str = get_settings().env
        self.tika_server_endpoint = self.config.dexit.tika_server_endpoint
        self.image_tag = "production" if self.env == "production" else "sprint"

    def payload(self: "DeploymentServer") -> dict:
        """
        Payload
        """
        body = k8s_client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=k8s_client.V1ObjectMeta(
                name="dexit",
                namespace=self.dexit.tenant,
            ),
            spec=k8s_client.V1DeploymentSpec(
                replicas=1,
                selector=k8s_client.V1LabelSelector(match_labels={"app": "dexit"}),
                template=k8s_client.V1PodTemplateSpec(
                    metadata=k8s_client.V1ObjectMeta(labels={"app": "dexit"}),
                    spec=k8s_client.V1PodSpec(
                        image_pull_secrets=[k8s_client.V1LocalObjectReference(name="registrycred")],
                        node_selector={"app": "314e"},
                        containers=[
                            k8s_client.V1Container(
                                name="dexit",
                                image=f"registry.314ecorp.tech/dexit-app:{self.image_tag}",
                                image_pull_policy="Always",
                                resources=k8s_client.V1ResourceRequirements(
                                    requests={
                                        "cpu": self.dexit.serverSpec.request_cpu,
                                        "memory": self.dexit.serverSpec.request_memory,
                                    },
                                    limits={
                                        "cpu": self.dexit.serverSpec.limit_cpu,
                                        "memory": self.dexit.serverSpec.limit_memory,
                                    },
                                ),
                                ports=[k8s_client.V1ContainerPort(name="http", protocol="TCP", container_port=8000)],
                                volume_mounts=[
                                    k8s_client.V1VolumeMount(
                                        name="env-volume",
                                        mount_path="/config/env-config.json",
                                        sub_path="env-config.json",
                                    ),
                                    k8s_client.V1VolumeMount(
                                        name="tenant-volume",
                                        mount_path="/config/tenant-config.json",
                                        sub_path="tenant-config.json",
                                    ),
                                ],
                                env=[
                                    k8s_client.V1EnvVar(name="DEPLOYMENT", value=self.env),
                                    k8s_client.V1EnvVar(
                                        name="POSTGRES_PASSWORD",
                                        value_from=k8s_client.V1EnvVarSource(
                                            secret_key_ref=k8s_client.V1SecretKeySelector(
                                                key="POSTGRES_PASSWORD", name="dexit-postgres-password"
                                            )
                                        ),
                                    ),
                                    k8s_client.V1EnvVar(name="POSTGRES_USER", value=self.postgres_user),
                                    k8s_client.V1EnvVar(
                                        name="RELEASE_VERSION",
                                        value=self.image_tag,
                                    ),
                                    k8s_client.V1EnvVar(name="APP_CONFIG_DIR", value="/config"),
                                    k8s_client.V1EnvVar(name="CLIENT_CODE", value=self.dexit.tenant),
                                    k8s_client.V1EnvVar(name="TIKA_SERVER_ENDPOINT", value=self.tika_server_endpoint),
                                    k8s_client.V1EnvVar(name="CLI", value="FALSE"),
                                ],
                            )
                        ],
                        volumes=[
                            k8s_client.V1Volume(
                                name="env-volume",
                                config_map=k8s_client.V1ConfigMapVolumeSource(
                                    name="dexit-env-config",
                                    items=[k8s_client.V1KeyToPath(key="env-config.json", path="env-config.json")],
                                ),
                            ),
                            k8s_client.V1Volume(
                                name="tenant-volume",
                                config_map=k8s_client.V1ConfigMapVolumeSource(
                                    name="dexit-tenant-config",
                                    items=[k8s_client.V1KeyToPath(key="tenant-config.json", path="tenant-config.json")],
                                ),
                            ),
                            k8s_client.V1Volume(
                                name="vespa-volume",
                                persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(
                                    claim_name="dexit-vespa-pvc"
                                ),
                            ),
                        ],
                    ),
                ),
            ),
        )

        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self: "DeploymentServer") -> None:
        """
        Put
        """
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource, body=self.payload(), field_manager="kubectl-client-side-apply"
        )
        log_info(message=f"dexit deployment created in namespace {self.dexit.tenant}")

    def delete(self: "DeploymentServer") -> None:
        """
        Delete
        """
        try:
            self.k8s_dynamic_client.delete(resource=self.resource, name=ProductName, namespace=self.dexit.tenant)
        except NotFoundError:
            logger.error("dexit deployment doesn't exist")


class DeploymentCli(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self: "DeploymentCli", dexit: DexitSpec) -> None:
        """
        Initialize DeploymentCli
        """
        self.dexit: DexitSpec = dexit
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Deployment, api_version="apps/v1"
        )
        self.config: AppSettings = get_settings()

        self.postgres_user = f"dexit_{dexit.tenant}"
        self.env: str = get_settings().env
        self.tika_server_endpoint = self.config.jeeves.tika_server_endpoint
        self.image_tag = "production" if self.env == "production" else "sprint"

    def payload(self: "DeploymentCli") -> dict:
        """
        Payload
        """
        body = k8s_client.V1Deployment = k8s_client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=k8s_client.V1ObjectMeta(
                name="dexit-cli",
                namespace=self.dexit.tenant,
            ),
            spec=k8s_client.V1DeploymentSpec(
                replicas=1,
                selector=k8s_client.V1LabelSelector(match_labels={"app": "dexit-cli"}),
                template=k8s_client.V1PodTemplateSpec(
                    metadata=k8s_client.V1ObjectMeta(labels={"app": "dexit-cli"}),
                    spec=k8s_client.V1PodSpec(
                        image_pull_secrets=[k8s_client.V1LocalObjectReference(name="registrycred")],
                        node_selector={"app": "314e"},
                        containers=[
                            k8s_client.V1Container(
                                name="dexit",
                                image=f"registry.314ecorp.tech/dexit-app:{self.image_tag}",
                                resources=k8s_client.V1ResourceRequirements(
                                    requests={
                                        "cpu": self.dexit.cliSpec.request_cpu,
                                        "memory": self.dexit.cliSpec.request_memory,
                                    },
                                    limits={
                                        "cpu": self.dexit.cliSpec.limit_cpu,
                                        "memory": self.dexit.cliSpec.limit_memory,
                                    },
                                ),
                                ports=[k8s_client.V1ContainerPort(name="http", protocol="TCP", container_port=8000)],
                                image_pull_policy="Always",
                                volume_mounts=[
                                    k8s_client.V1VolumeMount(
                                        name="env-volume",
                                        mount_path="/config/env-config.json",
                                        sub_path="env-config.json",
                                    ),
                                    k8s_client.V1VolumeMount(
                                        name="tenant-volume",
                                        mount_path="/config/tenant-config.json",
                                        sub_path="tenant-config.json",
                                    ),
                                    k8s_client.V1VolumeMount(
                                        name="vector-volume", mount_path="/vector", read_only=True
                                    ),
                                ],
                                env=[
                                    k8s_client.V1EnvVar(name="DEPLOYMENT", value=self.env),
                                    k8s_client.V1EnvVar(
                                        name="POSTGRES_PASSWORD",
                                        value_from=k8s_client.V1EnvVarSource(
                                            secret_key_ref=k8s_client.V1SecretKeySelector(
                                                key="POSTGRES_PASSWORD", name="dexit-postgres-password"
                                            )
                                        ),
                                    ),
                                    k8s_client.V1EnvVar(name="POSTGRES_USER", value=self.postgres_user),
                                    k8s_client.V1EnvVar(
                                        name="RELEASE_VERSION",
                                        value=self.image_tag,
                                    ),
                                    k8s_client.V1EnvVar(name="APP_CONFIG_DIR", value="/config"),
                                    k8s_client.V1EnvVar(name="CLIENT_CODE", value=self.dexit.tenant),
                                    k8s_client.V1EnvVar(name="TIKA_SERVER_ENDPOINT", value=self.tika_server_endpoint),
                                    k8s_client.V1EnvVar(name="CLI", value="TRUE"),
                                ],
                            )
                        ],
                        volumes=[
                            k8s_client.V1Volume(
                                name="env-volume",
                                config_map=k8s_client.V1ConfigMapVolumeSource(
                                    name="dexit-env-config",
                                    items=[k8s_client.V1KeyToPath(key="env-config.json", path="env-config.json")],
                                ),
                            ),
                            k8s_client.V1Volume(
                                name="tenant-volume",
                                config_map=k8s_client.V1ConfigMapVolumeSource(
                                    name="dexit-tenant-config",
                                    items=[k8s_client.V1KeyToPath(key="tenant-config.json", path="tenant-config.json")],
                                ),
                            ),
                            k8s_client.V1Volume(
                                name="vector-volume",
                                config_map=k8s_client.V1ConfigMapVolumeSource(
                                    name="dexit-cli-vector-config",
                                    items=[k8s_client.V1KeyToPath(key="vector-config.toml", path="vector-config.toml")],
                                ),
                            ),
                            k8s_client.V1Volume(
                                name="vespa-volume",
                                persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(
                                    claim_name="dexit-vespa-pvc"
                                ),
                            ),
                        ],
                    ),
                ),
            ),
        )

        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self: "DeploymentCli") -> None:
        """
        Put
        """
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource, body=self.payload(), field_manager="kubectl-client-side-apply"
        )
        log_info(message=f"dexit-cli deployment created in namespace {self.dexit.tenant}")

    def delete(self: "DeploymentCli") -> None:
        """
        Delete
        """
        try:
            self.k8s_dynamic_client.delete(resource=self.resource, name="dexit-cli", namespace=self.dexit.tenant)
        except NotFoundError:
            logger.error("dexit-cli deployment doesn't exist")
