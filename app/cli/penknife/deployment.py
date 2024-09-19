from kubernetes import client as k8s_client
from kubernetes.client import V1PersistentVolumeClaimVolumeSource
from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.penknife.models.penknifespec import PenknifeSpec
from app.cli.penknife.penknife import ProductName
from app.cli.temporal.core.log import log_info
from app.core.settings import get_settings, AppSettings
from app.onepasswordutil import OnePasswordUtil


class DeploymentServer(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self: "DeploymentServer", penknife: PenknifeSpec) -> None:
        """
        Constructor for DeploymentServer class
        """
        self.penknife: PenknifeSpec = penknife
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Deployment, api_version="apps/v1"
        )

        self.config: AppSettings = get_settings()
        self.env: str = self.config.env

        self.postgres_user = f"penknife_{self.penknife.tenant}"
        self.postgres_password = OnePasswordUtil(
            tenant=f"Penknife_{penknife.tenant}",
            server_item="application-config",
            vault="penknife",
        ).get_key("pg_password")

        self.image_tag = "production" if self.env == "production" else "sprint"

    def payload(self: "DeploymentServer") -> dict:
        """
        Payload for DeploymentServer
        """
        body = k8s_client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=k8s_client.V1ObjectMeta(
                name=ProductName,
                namespace=self.penknife.tenant,
            ),
            spec=k8s_client.V1DeploymentSpec(
                replicas=1,
                selector=k8s_client.V1LabelSelector(match_labels={"app": ProductName}),
                template=k8s_client.V1PodTemplateSpec(
                    metadata=k8s_client.V1ObjectMeta(labels={"app": ProductName}),
                    spec=k8s_client.V1PodSpec(
                        image_pull_secrets=[k8s_client.V1LocalObjectReference(name="registrycred")],
                        node_selector={"app": "314e"},
                        containers=[
                            k8s_client.V1Container(
                                name=ProductName,
                                image=f"registry.314ecorp.tech/penknife-app:{self.image_tag}",
                                image_pull_policy="Always",
                                resources=k8s_client.V1ResourceRequirements(
                                    requests={
                                        "cpu": self.penknife.serverSpec.request_cpu,
                                        "memory": self.penknife.serverSpec.request_memory,
                                    },
                                    limits={
                                        "cpu": self.penknife.serverSpec.limit_cpu,
                                        "memory": self.penknife.serverSpec.limit_memory,
                                    },
                                ),
                                security_context=k8s_client.V1SecurityContext(privileged=True),
                                ports=[k8s_client.V1ContainerPort(name="http", protocol="TCP", container_port=8000)],
                                volume_mounts=[
                                    k8s_client.V1VolumeMount(
                                        name="tenant-volume",
                                        mount_path="/config/tenant-config.json",
                                        sub_path="tenant-config.json",
                                    ),
                                    k8s_client.V1VolumeMount(
                                        name="rclone-volume", mount_path="/root/.config/rclone/", read_only=True
                                    ),
                                    k8s_client.V1VolumeMount(
                                        name="statestore-volume",
                                        mount_path="/root/.dapr/components/statestore.yaml",
                                        sub_path="statestore.yaml",
                                    ),
                                ],
                                env=[
                                    k8s_client.V1EnvVar(name="DEPLOYMENT", value=self.env),
                                    k8s_client.V1EnvVar(name="CLIENT_CODE", value=self.penknife.tenant),
                                    k8s_client.V1EnvVar(name="APP_CONFIG_FILE", value="/config/tenant-config.json"),
                                    k8s_client.V1EnvVar(name="POSTGRES_PASSWORD", value=self.postgres_password),
                                    k8s_client.V1EnvVar(name="POSTGRES_USER", value=self.postgres_user),
                                    k8s_client.V1EnvVar(name="EXTRACTOR_ENABLED", value="FALSE")
                                ],
                            )
                        ],
                        volumes=[
                            k8s_client.V1Volume(
                                name="tenant-volume",
                                config_map=k8s_client.V1ConfigMapVolumeSource(
                                    name="penknife-tenant-config",
                                    items=[k8s_client.V1KeyToPath(key="tenant-config.json", path="tenant-config.json")],
                                ),
                            ),
                            k8s_client.V1Volume(
                                name="rclone-volume",
                                config_map=k8s_client.V1ConfigMapVolumeSource(
                                    name="penknife-rclone-config",
                                    items=[k8s_client.V1KeyToPath(key="rclone.conf", path="rclone.conf")],
                                ),
                            ),
                            k8s_client.V1Volume(
                                name="statestore-volume",
                                config_map=k8s_client.V1ConfigMapVolumeSource(
                                    name="penknife-statestore-config",
                                    items=[k8s_client.V1KeyToPath(key="statestore.yaml", path="statestore.yaml")],
                                ),
                            ),
                            # k8s_client.V1Volume(
                            #     name="vespa-volume",
                            #     persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(
                            #         claim_name="penknife-vespa-pvc"
                            #     ),
                            # ),
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
        log_info(f"Deployment {ProductName} created in namespace {self.penknife.tenant}")

    def delete(self: "DeploymentServer") -> None:
        """
        Delete
        """
        try:
            self.k8s_dynamic_client.delete(resource=self.resource, name=ProductName, namespace=self.penknife.tenant)
        except NotFoundError:
            logger.error("penknife deployment doesn't exist")


class DeploymentCli(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self: "DeploymentCli", penknife: PenknifeSpec) -> None:
        """
        Constructor for DeploymentCli class
        """
        self.penknife: PenknifeSpec = penknife
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Deployment, api_version="apps/v1"
        )

        self.config: AppSettings = get_settings()
        self.env: str = self.config.env

        self.postgres_user = f"penknife_{self.penknife.tenant}"
        self.postgres_password = OnePasswordUtil(
            tenant=f"Penknife_{penknife.tenant}",
            server_item="application-config",
            vault="Penknife",
        ).get_key("pg_password")

        self.image_tag = "production" if self.env == "production" else "sprint"

    def payload(self: "DeploymentCli") -> dict:
        """
        Payload
        """
        body = k8s_client.V1Deployment = k8s_client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=k8s_client.V1ObjectMeta(
                name="penknife-cli",
                namespace=self.penknife.tenant,
            ),
            spec=k8s_client.V1DeploymentSpec(
                replicas=1,
                selector=k8s_client.V1LabelSelector(match_labels={"app": "penknife-cli"}),
                template=k8s_client.V1PodTemplateSpec(
                    metadata=k8s_client.V1ObjectMeta(labels={"app": "penknife-cli"}),
                    spec=k8s_client.V1PodSpec(
                        image_pull_secrets=[k8s_client.V1LocalObjectReference(name="registrycred")],
                        node_selector={"app": "314e"},
                        containers=[
                            k8s_client.V1Container(
                                name="penknife",
                                image=f"registry.314ecorp.tech/penknife-app:{self.image_tag}",
                                resources=k8s_client.V1ResourceRequirements(
                                    requests={
                                        "cpu": self.penknife.cliSpec.request_cpu,
                                        "memory": self.penknife.cliSpec.request_memory,
                                    },
                                    limits={
                                        "cpu": self.penknife.cliSpec.limit_cpu,
                                        "memory": self.penknife.cliSpec.limit_memory,
                                    },
                                ),
                                ports=[k8s_client.V1ContainerPort(name="http", protocol="TCP", container_port=8000)],
                                image_pull_policy="Always",
                                volume_mounts=[
                                    k8s_client.V1VolumeMount(
                                        name="tenant-volume",
                                        mount_path="/config/tenant-config.json",
                                        sub_path="tenant-config.json",
                                    ),
                                    k8s_client.V1VolumeMount(
                                        name="vector-volume", mount_path="/vector", read_only=True
                                    ),
                                    k8s_client.V1VolumeMount(
                                        name="rclone-volume", mount_path="/root/.config/rclone/", read_only=True
                                    ),
                                    k8s_client.V1VolumeMount(
                                        name="statestore-volume",
                                        mount_path="/root/.dapr/components/statestore.yaml",
                                        sub_path="statestore.yaml",
                                    ),
                                ],
                                env=[
                                    k8s_client.V1EnvVar(name="DEPLOYMENT", value=self.env),
                                    k8s_client.V1EnvVar(name="CLIENT_CODE", value=self.penknife.tenant),
                                    k8s_client.V1EnvVar(name="APP_CONFIG_FILE", value="/config/tenant-config.json"),
                                    k8s_client.V1EnvVar(name="POSTGRES_PASSWORD", value=self.postgres_password),
                                    k8s_client.V1EnvVar(name="POSTGRES_USER", value=self.postgres_user),
                                    k8s_client.V1EnvVar(name="EXTRACTOR_ENABLED", value="TRUE")
                                ],
                            )
                        ],
                        volumes=[
                            k8s_client.V1Volume(
                                name="tenant-volume",
                                config_map=k8s_client.V1ConfigMapVolumeSource(
                                    name="penknife-tenant-config",
                                    items=[k8s_client.V1KeyToPath(key="tenant-config.json", path="tenant-config.json")],
                                ),
                            ),
                            k8s_client.V1Volume(
                                name="rclone-volume",
                                config_map=k8s_client.V1ConfigMapVolumeSource(
                                    name="penknife-rclone-config",
                                    items=[k8s_client.V1KeyToPath(key="rclone.conf", path="rclone.conf")],
                                ),
                            ),
                            k8s_client.V1Volume(
                                name="vector-volume",
                                config_map=k8s_client.V1ConfigMapVolumeSource(
                                    name="penknife-cli-vector-config",
                                    items=[k8s_client.V1KeyToPath(key="vector-config.toml", path="vector-config.toml")],
                                ),
                            ),
                            k8s_client.V1Volume(
                                name="statestore-volume",
                                config_map=k8s_client.V1ConfigMapVolumeSource(
                                    name="penknife-statestore-config",
                                    items=[k8s_client.V1KeyToPath(key="statestore.yaml", path="statestore.yaml")],
                                ),
                            ),
                            # k8s_client.V1Volume(
                            #     name="vespa-volume",
                            #     persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(
                            #         claim_name="penknife-vespa-pvc"
                            #     ),
                            # ),
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
        log_info(f"Deployment penknife-cli created in namespace {self.penknife.tenant}")

    def delete(self: "DeploymentCli") -> None:
        """
        Delete
        """
        try:
            self.k8s_dynamic_client.delete(resource=self.resource, name="penknife-cli", namespace=self.penknife.tenant)
        except NotFoundError:
            logger.error("penknife-cli deployment doesn't exist")
