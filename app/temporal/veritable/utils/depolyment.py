from kubernetes import client as k8s_client

from app.onepasswordutil import OnePasswordUtil
from app.temporal.common.deployment import DeploymentJob
from app.temporal.veritable.utils.common import VeritableSpec, OnepasswordItemName, OnepasswordVaultName, ProductName


async def deploy_server_and_cli(veritable: VeritableSpec):
    """
    Deploy server and CLI
    """
    # deploy server and CLI in k8s

    postgres_user = f"veritable_{veritable.tenant}"
    postgres_password = OnePasswordUtil(
        tenant=veritable.tenant,
        server_item=OnepasswordItemName.format(environment=veritable.environment),
        vault=OnepasswordVaultName
    ).get_key("postgres_database_password")

    # create server deployment
    k8s_deployment = DeploymentJob(
        namespace=veritable.tenant,
        deployment_name=ProductName,
        product_name=ProductName,
    )

    server_deployment_body: k8s_client.V1Deployment = k8s_client.V1Deployment(
        kind="Deployment",
        metadata=k8s_client.V1ObjectMeta(
            name=f"veritable",
            namespace=veritable.tenant,
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
                            image=f"registry.314ecorp.tech/veritable-server:{veritable.imageTag}",
                            image_pull_policy="Always",
                            resources=k8s_client.V1ResourceRequirements(
                                requests={
                                    "cpu": veritable.serverSpec.request_cpu,
                                    "memory": veritable.serverSpec.request_memory
                                },
                                limits={
                                    "cpu": veritable.serverSpec.limit_cpu,
                                    "memory": veritable.serverSpec.limit_memory
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
                                    value=veritable.environment
                                ),
                                k8s_client.V1EnvVar(
                                    name="POSTGRES__PASSWORD",
                                    value=postgres_password
                                ),
                                k8s_client.V1EnvVar(
                                    name="POSTGRES__USER",
                                    value=postgres_user
                                ),
                                k8s_client.V1EnvVar(
                                    name="RELEASE_VERSION",
                                    value=veritable.imageTag,
                                ),
                                k8s_client.V1EnvVar(
                                    name="APP_CONFIG_DIR",
                                    value="/config"
                                ),
                                k8s_client.V1EnvVar(
                                    name="CLIENT_CODE",
                                    value=veritable.tenant
                                ),
                                k8s_client.V1EnvVar(
                                    name="IS_CLI",
                                    value="FALSE"
                                ),
                                k8s_client.V1EnvVar(
                                    name="ORG_NAME",
                                    value=veritable.orgName
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
                                items=[k8s_client.V1KeyToPath(key="veritable-tenant-config", path="tenant-config.json")]
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

    await k8s_deployment.create_or_replace(server_deployment_body)

    # create temporal deployment

    cli_deployment_body: k8s_client.V1Deployment = k8s_client.V1Deployment(
        kind="Deployment",
        metadata=k8s_client.V1ObjectMeta(
            name=f"veritable-temporal",
            namespace=veritable.tenant,
        ),
        spec=k8s_client.V1DeploymentSpec(
            replicas=1,
            selector=k8s_client.V1LabelSelector(
                match_labels={"app": "veritable-temporal"}
            ),
            template=k8s_client.V1PodTemplateSpec(
                metadata=k8s_client.V1ObjectMeta(
                    labels={"app": "veritable-temporal"}
                ),
                spec=k8s_client.V1PodSpec(
                    image_pull_secrets=[k8s_client.V1LocalObjectReference(name="registrycred")],
                    node_selector={"app": "314e"},
                    containers=[
                        k8s_client.V1Container(
                            name="veritable",
                            image=f"registry.314ecorp.tech/veritable-server:{veritable.imageTag}",
                            resources=k8s_client.V1ResourceRequirements(
                                requests={
                                    "cpu": veritable.cliSpec.request_cpu,
                                    "memory": veritable.cliSpec.request_memory
                                },
                                limits={
                                    "cpu": veritable.cliSpec.limit_cpu,
                                    "memory": veritable.cliSpec.limit_memory
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
                                    value=veritable.environment
                                ),
                                k8s_client.V1EnvVar(
                                    name="POSTGRES__PASSWORD",
                                    value=postgres_password
                                ),
                                k8s_client.V1EnvVar(
                                    name="POSTGRES__USER",
                                    value=postgres_user
                                ),
                                k8s_client.V1EnvVar(
                                    name="RELEASE_VERSION",
                                    value=veritable.imageTag,
                                ),
                                k8s_client.V1EnvVar(
                                    name="APP_CONFIG_DIR",
                                    value="/config"
                                ),
                                k8s_client.V1EnvVar(
                                    name="CLIENT_CODE",
                                    value=veritable.tenant
                                ),
                                k8s_client.V1EnvVar(
                                    name="IS_CLI",
                                    value="TRUE"
                                ),
                                k8s_client.V1EnvVar(
                                    name="ORG_NAME",
                                    value=veritable.orgName
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
                                items=[k8s_client.V1KeyToPath(key="veritable-tenant-config", path="tenant-config.json")]
                            )
                        ),
                        k8s_client.V1Volume(
                            name="vector-volume",
                            config_map=k8s_client.V1ConfigMapVolumeSource(
                                name="veritable-temporal-vector-config",
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

    # create deployment
    k8s_deployment = DeploymentJob(
        namespace=veritable.tenant,
        deployment_name=f"{ProductName}-temporal",
        product_name=ProductName,
    )

    await k8s_deployment.create_or_replace(cli_deployment_body)
