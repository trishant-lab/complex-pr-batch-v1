from kubernetes import client as k8s_client
from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.veritable.models.configmap import TenantMapClass, EnvMapClass, VectorMapClass
from app.cli.veritable.models.labels import CLi_DEPLOYMENT_LABELS
from app.cli.veritable.models.VeritableSpec import VeritableSpec
from app.cli.veritable.veritable import ProductName
from app.core.settings import get_settings


class DeploymentCli(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self: "DeploymentCli", veritable: VeritableSpec) -> None:
        """
        Constructor
        """
        self.veritable: VeritableSpec = veritable
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Deployment, api_version="apps/v1"
        )

        self.postgres_user = f"veritable_{veritable.tenant}"
        self.env: str = get_settings().env

    def payload(self: "DeploymentCli") -> dict:
        """
        Payload
        """
        body = k8s_client.V1Deployment = k8s_client.V1Deployment(
            api_version="apps/v1",
            kind=ResourceKindEnum.Deployment.value,
            metadata=k8s_client.V1ObjectMeta(
                name=f"{ProductName}-cli",
                namespace=self.veritable.tenant,
            ),
            spec=k8s_client.V1DeploymentSpec(
                replicas=1,
                selector=k8s_client.V1LabelSelector(match_labels=CLi_DEPLOYMENT_LABELS),
                template=k8s_client.V1PodTemplateSpec(
                    metadata=k8s_client.V1ObjectMeta(labels=CLi_DEPLOYMENT_LABELS),
                    spec=k8s_client.V1PodSpec(
                        image_pull_secrets=[k8s_client.V1LocalObjectReference(name="registrycred")],
                        node_selector={"app": "314e"},
                        containers=[
                            k8s_client.V1Container(
                                name=f"{ProductName}-cli",
                                image=f"registry.314ecorp.tech/veritable-server:{self.veritable.imageTag}",
                                resources=k8s_client.V1ResourceRequirements(
                                    requests={
                                        "cpu": self.veritable.cliSpec.request_cpu,
                                        "memory": self.veritable.cliSpec.request_memory,
                                    },
                                    limits={
                                        "cpu": self.veritable.cliSpec.limit_cpu,
                                        "memory": self.veritable.cliSpec.limit_memory,
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
                                    k8s_client.V1VolumeMount(name="veritable-pvc", mount_path="/data", read_only=False),
                                ],
                                env=[
                                    k8s_client.V1EnvVar(name="DEPLOYMENT", value=self.env),
                                    k8s_client.V1EnvVar(
                                        name="POSTGRES__PASSWORD",
                                        value_from=k8s_client.V1EnvVarSource(
                                            secret_key_ref=k8s_client.V1SecretKeySelector(
                                                key="password", name="veritable-postgres"
                                            )
                                        ),
                                    ),
                                    k8s_client.V1EnvVar(name="POSTGRES__USER", value=self.postgres_user),
                                    k8s_client.V1EnvVar(
                                        name="RELEASE_VERSION",
                                        value=self.veritable.imageTag,
                                    ),
                                    k8s_client.V1EnvVar(name="APP_CONFIG_DIR", value="/config"),
                                    k8s_client.V1EnvVar(name="CLIENT_CODE", value=self.veritable.tenant),
                                    k8s_client.V1EnvVar(name="IS_CLI", value="TRUE"),
                                    k8s_client.V1EnvVar(
                                        name="ORG_NAME", value=self.veritable.customerDetails.organization
                                    ),
                                ],
                            )
                        ],
                        volumes=[
                            k8s_client.V1Volume(
                                name="env-volume",
                                config_map=k8s_client.V1ConfigMapVolumeSource(
                                    name=EnvMapClass.name,
                                    items=[k8s_client.V1KeyToPath(key=EnvMapClass.key, path="env-config.json")],
                                ),
                            ),
                            k8s_client.V1Volume(
                                name="tenant-volume",
                                config_map=k8s_client.V1ConfigMapVolumeSource(
                                    name=TenantMapClass.name,
                                    items=[k8s_client.V1KeyToPath(key=TenantMapClass.key, path="tenant-config.json")],
                                ),
                            ),
                            k8s_client.V1Volume(
                                name="vector-volume",
                                config_map=k8s_client.V1ConfigMapVolumeSource(
                                    name=VectorMapClass.name,
                                    items=[k8s_client.V1KeyToPath(key=VectorMapClass.key, path="vector-config.toml")],
                                ),
                            ),
                            k8s_client.V1Volume(
                                name="veritable-pvc",
                                persistent_volume_claim=k8s_client.V1PersistentVolumeClaimVolumeSource(
                                    claim_name="veritable-pvc"
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

    def delete(self: "DeploymentCli") -> None:
        """
        Delete
        """
        try:
            self.k8s_dynamic_client.delete(
                resource=self.resource, name="veritable-cli", namespace=self.veritable.tenant
            )
        except NotFoundError:
            logger.error("veritable-cli deployment doesn't exist")
