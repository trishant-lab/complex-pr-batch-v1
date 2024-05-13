from kubernetes import client as k8s_client
from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.veritable.common import OnepasswordItemName, OnepasswordVaultName, ProductName
from app.cli.veritable.common import VeritableSpec
from app.core.settings import get_settings
from app.onepasswordutil import OnePasswordUtil


class DeploymentServer(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self, veritable: VeritableSpec) -> None:
        self.veritable: VeritableSpec = veritable
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Deployment, api_version="apps/v1"
        )

        self.postgres_user = f"veritable_{veritable.tenant}"
        self.env: str = get_settings().env

        # Todo change it to get kube secret
        self.postgres_password = OnePasswordUtil(
            tenant=veritable.tenant,
            server_item=OnepasswordItemName.format(environment=self.env),
            vault=OnepasswordVaultName
        ).get_key("postgres_database_password")

    def payload(self):
        body = k8s_client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=k8s_client.V1ObjectMeta(
                name=f"veritable",
                namespace=self.veritable.tenant,
            ),
            spec=k8s_client.V1DeploymentSpec(
                replicas=1,
                selector=k8s_client.V1LabelSelector(
                    match_labels={"app": "veritable"}
                ),
                template=k8s_client.V1PodTemplateSpec(
                    metadata=k8s_client.V1ObjectMeta(
                        labels={"app": "veritable"}
                    ),
                    spec=k8s_client.V1PodSpec(
                        image_pull_secrets=[k8s_client.V1LocalObjectReference(name="registrycred")],
                        node_selector={"app": "314e"},
                        containers=[
                            k8s_client.V1Container(
                                name="veritable",
                                image=f"registry.314ecorp.tech/veritable-server:{self.veritable.imageTag}",
                                image_pull_policy="Always",
                                resources=k8s_client.V1ResourceRequirements(
                                    requests={
                                        "cpu": self.veritable.serverSpec.request_cpu,
                                        "memory": self.veritable.serverSpec.request_memory
                                    },
                                    limits={
                                        "cpu": self.veritable.serverSpec.limit_cpu,
                                        "memory": self.veritable.serverSpec.limit_memory
                                    },
                                ),
                                ports=[
                                    k8s_client.V1ContainerPort(
                                        name="http",
                                        protocol="TCP",
                                        container_port=8000
                                    )
                                ],
                                volume_mounts=[
                                    k8s_client.V1VolumeMount(
                                        name="env-volume",
                                        mount_path="/config/env-config.json",
                                        sub_path="env-config.json"
                                    ),
                                    k8s_client.V1VolumeMount(
                                        name="tenant-volume",
                                        mount_path="/config/tenant-config.json",
                                        sub_path="tenant-config.json"
                                    )
                                ],
                                env=[
                                    k8s_client.V1EnvVar(
                                        name="DEPLOYMENT",
                                        value=self.env
                                    ),
                                    k8s_client.V1EnvVar(
                                        name="POSTGRES__PASSWORD",
                                        value=self.postgres_password
                                    ),
                                    k8s_client.V1EnvVar(
                                        name="POSTGRES__USER",
                                        value=self.postgres_password
                                    ),
                                    k8s_client.V1EnvVar(
                                        name="RELEASE_VERSION",
                                        value=self.veritable.imageTag,
                                    ),
                                    k8s_client.V1EnvVar(
                                        name="APP_CONFIG_DIR",
                                        value="/config"
                                    ),
                                    k8s_client.V1EnvVar(
                                        name="CLIENT_CODE",
                                        value=self.veritable.tenant
                                    ),
                                    k8s_client.V1EnvVar(
                                        name="IS_CLI",
                                        value="FALSE"
                                    ),
                                    k8s_client.V1EnvVar(
                                        name="ORG_NAME",
                                        value=self.veritable.orgName
                                    )
                                ]
                            )
                        ],
                        volumes=[
                            k8s_client.V1Volume(
                                name="env-volume",
                                config_map=k8s_client.V1ConfigMapVolumeSource(
                                    name="veritable-env-config",
                                    items=[k8s_client.V1KeyToPath(key="env-config.json", path="env-config.json")]
                                )
                            ),
                            k8s_client.V1Volume(
                                name="tenant-volume",
                                config_map=k8s_client.V1ConfigMapVolumeSource(
                                    name="veritable-tenant-config",
                                    items=[k8s_client.V1KeyToPath(
                                        key="veritable-tenant-config", path="tenant-config.json"
                                    )]
                                )
                            ),
                            k8s_client.V1Volume(
                                name="provisioning-volume",
                                config_map=k8s_client.V1ConfigMapVolumeSource(
                                    name="veritable-provisioning-config",
                                    items=[k8s_client.V1KeyToPath(
                                        key="provisioning-config.json", path="provisioning-config.json"
                                    )]
                                )
                            )
                        ]
                    )
                )
            )
        )

        deployment_body = self.k8s_dynamic_client.client.sanitize_for_serialization(body)
        logger.info(f"Deployment payload: {deployment_body}")
        return deployment_body

    def put(self):
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource,
            body=self.payload(),
            field_manager="kubectl-client-side-apply"
        )

    def delete(self):
        try:
            self.k8s_dynamic_client.delete(
                resource=self.resource,
                name=ProductName,
                namespace=self.veritable.tenant
            )
        except NotFoundError:
            logger.error(f"veritable deployment doesn't exist")


class DeploymentCli(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self, veritable: VeritableSpec) -> None:
        self.veritable: VeritableSpec = veritable
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Deployment, api_version="apps/v1"
        )

        self.postgres_user = f"veritable_{veritable.tenant}"
        self.env: str = get_settings().env

        # Todo change it to get kube secret
        self.postgres_password = OnePasswordUtil(
            tenant=veritable.tenant,
            server_item=OnepasswordItemName.format(environment=self.env),
            vault=OnepasswordVaultName
        ).get_key("postgres_database_password")

    def payload(self):
        body = k8s_client.V1Deployment = k8s_client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=k8s_client.V1ObjectMeta(
                name=f"veritable-cli",
                namespace=self.veritable.tenant,
            ),
            spec=k8s_client.V1DeploymentSpec(
                replicas=1,
                selector=k8s_client.V1LabelSelector(
                    match_labels={"app": "veritable-cli"}
                ),
                template=k8s_client.V1PodTemplateSpec(
                    metadata=k8s_client.V1ObjectMeta(
                        labels={"app": "veritable-cli"}
                    ),
                    spec=k8s_client.V1PodSpec(
                        image_pull_secrets=[k8s_client.V1LocalObjectReference(name="registrycred")],
                        node_selector={"app": "314e"},
                        containers=[
                            k8s_client.V1Container(
                                name="veritable",
                                image=f"registry.314ecorp.tech/veritable-server:{self.veritable.imageTag}",
                                resources=k8s_client.V1ResourceRequirements(
                                    requests={
                                        "cpu": self.veritable.cliSpec.request_cpu,
                                        "memory": self.veritable.cliSpec.request_memory
                                    },
                                    limits={
                                        "cpu": self.veritable.cliSpec.limit_cpu,
                                        "memory": self.veritable.cliSpec.limit_memory
                                    },
                                ),
                                ports=[
                                    k8s_client.V1ContainerPort(
                                        name="http",
                                        protocol="TCP",
                                        container_port=8000
                                    )
                                ],
                                image_pull_policy="Always",
                                volume_mounts=[
                                    k8s_client.V1VolumeMount(
                                        name="env-volume",
                                        mount_path="/config/env-config.json",
                                        sub_path="env-config.json"
                                    ),
                                    k8s_client.V1VolumeMount(
                                        name="tenant-volume",
                                        mount_path="/config/tenant-config.json",
                                        sub_path="tenant-config.json"
                                    ),
                                    k8s_client.V1VolumeMount(
                                        name="vector-volume",
                                        mount_path="/vector",
                                        read_only=True
                                    ),
                                    k8s_client.V1VolumeMount(
                                        name="veritable-pvc",
                                        mount_path="/data",
                                        read_only=False
                                    )
                                ],
                                env=[
                                    k8s_client.V1EnvVar(
                                        name="DEPLOYMENT",
                                        value=self.env
                                    ),
                                    k8s_client.V1EnvVar(
                                        name="POSTGRES__PASSWORD",
                                        value=self.postgres_password
                                    ),
                                    k8s_client.V1EnvFromSource(
                                        secret_ref=k8s_client.V1SecretEnvSource(
                                            name="veritable-postgres-secret",
                                        )
                                    ),
                                    k8s_client.V1EnvVar(
                                        name="POSTGRES__USER",
                                        value=self.postgres_user
                                    ),
                                    k8s_client.V1EnvVar(
                                        name="RELEASE_VERSION",
                                        value=self.veritable.imageTag,
                                    ),
                                    k8s_client.V1EnvVar(
                                        name="APP_CONFIG_DIR",
                                        value="/config"
                                    ),
                                    k8s_client.V1EnvVar(
                                        name="CLIENT_CODE",
                                        value=self.veritable.tenant
                                    ),
                                    k8s_client.V1EnvVar(
                                        name="IS_CLI",
                                        value="TRUE"
                                    ),
                                    k8s_client.V1EnvVar(
                                        name="ORG_NAME",
                                        value=self.veritable.orgName
                                    )
                                ]
                            )
                        ],
                        volumes=[
                            k8s_client.V1Volume(
                                name="env-volume",
                                config_map=k8s_client.V1ConfigMapVolumeSource(
                                    name="veritable-env-config",
                                    items=[k8s_client.V1KeyToPath(
                                        key="env-config.json", path="env-config.json"
                                    )]
                                )
                            ),
                            k8s_client.V1Volume(
                                name="tenant-volume",
                                config_map=k8s_client.V1ConfigMapVolumeSource(
                                    name="veritable-tenant-config",
                                    items=[k8s_client.V1KeyToPath(
                                        key="veritable-tenant-config", path="tenant-config.json"
                                    )]
                                )
                            ),
                            k8s_client.V1Volume(
                                name="vector-volume",
                                config_map=k8s_client.V1ConfigMapVolumeSource(
                                    name="veritable-cli-vector-config",
                                    items=[k8s_client.V1KeyToPath(key="vector-config.toml", path="vector-config.toml")]
                                )
                            ),
                            k8s_client.V1Volume(
                                name="veritable-pvc",
                                persistent_volume_claim=k8s_client.V1PersistentVolumeClaimVolumeSource(
                                    claim_name="veritable-pvc"
                                )
                            )
                        ]
                    )
                )
            )
        )

        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self):
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource,
            body=self.payload(),
            field_manager="kubectl-client-side-apply"
        )

    def delete(self):
        try:
            self.k8s_dynamic_client.delete(
                resource=self.resource,
                name=f"veritable-cli",
                namespace=self.veritable.tenant
            )
        except NotFoundError:
            logger.error(f"veritable-cli deployment doesn't exist")
