import time
from dataclasses import dataclass
from tempfile import TemporaryDirectory

import orjson
from cryptography.fernet import Fernet
from kubernetes import client, config as k8s_config
from kubernetes.client import ApiException
from loguru import logger
from temporalio import activity

from temporalio.client import WorkflowExecutionStatus

from app.core.settings import AppSettings, get_settings, ProductConfig
from app.temporalworkflows.common.GoogleDNS import GoogleDNS
from app.temporalworkflows.common.configmap import ConfigMap
from app.temporalworkflows.common.deployment import DeploymentJob
from app.temporalworkflows.common.grafanautils import GrafanaUtils
from app.temporalworkflows.common.istio_virtual_service import IstioVirtualService
from app.temporalworkflows.common.kubernetes_job import KubernetesJob
from app.temporalworkflows.common.kubernetes_service import KubernetesService
from app.temporalworkflows.common.minio_utils import deploy_ui
from app.temporalworkflows.common.postgresdatabasesetup.postgresdatabasesetuphelper import (
    trigger_postgres_database_setup_workflow
)
from app.temporalworkflows.common.keyclaokrealmsetup.keyclaokrealmcreationhelper import (
    trigger_keycloak_realm_creation_workflow
)

from app.temporalworkflows.common.namespacesetup import Namespace
from app.temporalworkflows.common.pvcsetup import PVC
from app.temporalworkflows.common.secrets import KubernetesSecretService
from app.temporalworkflows.common.vmpodscrapper import VMPodScrapper
from app.temporalworkflows.onepasswordutil import OnePasswordUtil, secret_inject
from app.temporalworkflows.template_env import get_env

from app.temporalworkflows.temporalUtils import check_workflow_status
from app.temporalworkflows.veritable.veritableSpec import VeritableSpec


@activity.defn
async def postgres_database_setup_activity(veritable: VeritableSpec) -> None:
    """
    :return:
    """

    database_name = f"veritable_{veritable.environment}"

    payload = {
        "product": "Veritable",
        "tenant": veritable.tenant,
        "env": veritable.environment,
        "database_name": database_name,
        "schema_name": f"veritable_{veritable.tenant}"
    }
    workflow_id = (
        f"postgres_database_setup_workflow_"
        f"{payload.get('product').lower()}-{payload.get('env')}-{payload.get('tenant')}"
    )
    await trigger_postgres_database_setup_workflow(payload, workflow_id)

    workflow_status = await check_workflow_status(workflow_id=workflow_id)

    logger.info(f"Workflow status: {workflow_status}")

    # wait for workflow to complete
    while workflow_status != WorkflowExecutionStatus.COMPLETED.name:

        if workflow_status in (
                WorkflowExecutionStatus.FAILED.name,
                WorkflowExecutionStatus.CANCELED.name,
                WorkflowExecutionStatus.TERMINATED.name,
        ):
            logger.error(f"Postgres database setup workflow {workflow_status} for {workflow_id}")
            raise Exception(f"Postgres database setup workflow {workflow_status} for {workflow_id}")

        time.sleep(5)
        workflow_status = await check_workflow_status(workflow_id=workflow_id)

    logger.info(f"Postgres database setup workflow completed for {workflow_id}")


@activity.defn
async def create_namespace_activity(veritable: VeritableSpec) -> None:
    """
    :return:
    """
    namespace = Namespace(namespace=f"{veritable.tenant}")
    await namespace.create()
    logger.info(f"Created namespace for {veritable.tenant}")


def apply_tenant_config(veritable: VeritableSpec):
    """
    :return:
    """
    template_env = get_env("veritable")
    template = template_env.get_template("integration-tenant-config.tmpl.json")
    output = template.render(
        tenant=veritable.tenant,
    )

    with TemporaryDirectory() as temp_dir:
        with open(f"{temp_dir}/integration-tenant-config.tmpl.json", "w") as f:
            f.write(output)

        # inject secret into tenant-config.json from 1Password
        secret_inject(
            source_file_path=f"{temp_dir}/integration-tenant-config.tmpl.json",
            destination_path=f"{temp_dir}/tenant-config.json"
        )

        # apply configmap in k8s namespace
        ConfigMap(namespace=veritable.tenant).create_or_replace_config(
            name="veritable-tenant-config",
            data={"veritable-tenant-config": open(f"{temp_dir}/tenant-config.json").read()}
        )


def apply_provisioning_config(veritable: VeritableSpec):
    """
    :return:
    """
    template_env = get_env("veritable")
    template = template_env.get_template("integration-provisioning-config.tmpl.json")
    output = template.render(
        tenant=veritable.tenant,
        customerId=veritable.customerId,
        orgName=veritable.orgName,
    )

    with TemporaryDirectory() as temp_dir:
        with open(f"{temp_dir}/integration-provisioning-config.tmpl.json", "w") as f:
            f.write(output)

        # inject secret into tenant-config.json from 1Password
        secret_inject(
            source_file_path=f"{temp_dir}/integration-provisioning-config.tmpl.json",
            destination_path=f"{temp_dir}/provisioning-config.json"
        )

        # apply configmap in k8s namespace
        ConfigMap(namespace=veritable.tenant).create_or_replace_config(
            name="veritable-provisioning-config",
            data={"provisioning-config.json": open(f"{temp_dir}/provisioning-config.json").read()}
        )


def apply_env_config(veritable: VeritableSpec):
    """
    :return:
    """

    template_env = get_env("veritable")
    template = template_env.get_template("integration-env-config.tmpl.json")
    output = template.render(
        tenant=veritable.tenant,
    )

    with TemporaryDirectory() as temp_dir:
        with open(f"{temp_dir}/integration-env-config.tmpl.json", "w") as f:
            f.write(output)

        # inject secret into tenant-config.json from 1Password
        secret_inject(
            source_file_path=f"{temp_dir}/integration-env-config.tmpl.json",
            destination_path=f"{temp_dir}/env-config.json"
        )

        # apply configmap in k8s namespace
        ConfigMap(namespace=veritable.tenant).create_or_replace_config(
            name="veritable-env-config",
            data={"env-config.json": open(f"{temp_dir}/env-config.json").read()}
        )


def apply_vector_config(veritable: VeritableSpec):
    """
    :return:

    """
    ConfigMap(namespace=veritable.tenant).create_or_replace_config(
        name="veritable-cli-vector-config",
        data={"vector-config.toml": "[log_schema]\nhost_key = \"host\"\nmessage_key = \"message\"\nsource_type_key = \"source_type\"\ntimestamp_key = \"timestamp\"\n\n# sources for logs\n\n[sources.custom_logs]\ntype = \"file\"\ninclude = [\"/var/log/supervisord/veritable_*\"]\nfingerprint.strategy = \"device_and_inode\"\n\n[sinks.vector_sink]\ntype = \"loki\"\ninputs = [ \"custom_logs\" ]\nendpoint = \"http://loki.monitoring-system.svc.cluster.local:3100\" \n[sinks.vector_sink.encoding]\ncodec = \"json\"\n[sinks.vector_sink.labels]\nname = \"veritable_custom_logs_" + veritable.tenant + "\""}  # noqa
    )


@activity.defn
async def create_configmap_activity(veritable: VeritableSpec) -> None:
    """
    Create configmap activity
    """
    product_config: ProductConfig = get_settings().product_config.get("veritable")
    # generate fernet key and insert into 1Password if not exists
    OnePasswordUtil(
        tenant=veritable.tenant,
        server_item=f"veritable-tenant-config-{veritable.environment}",
        vault=product_config.vault_name
    ).insert_if_not_exists("fernet_key", Fernet.generate_key().decode())

    apply_tenant_config(veritable)
    apply_provisioning_config(veritable)
    apply_env_config(veritable)
    apply_vector_config(veritable)


@activity.defn
async def create_pvc_activity(veritable: VeritableSpec) -> None:
    """
    :return:
    """
    namespace: str = veritable.tenant
    pvc = PVC(namespace=namespace, pvc_name=f"veritable-pvc", storage="200Mi")
    await pvc.create()
    logger.info(f"Created PVC for {veritable.tenant}")


@activity.defn
async def secret_setup_activity(veritable: VeritableSpec) -> None:
    """
    :return:
    """
    config: AppSettings = get_settings()

    namespace: str = veritable.tenant
    secret_name: str = f"registrycred"
    data: dict = {
        ".dockerconfigjson": config.docker_image_pull_secret
    }
    secret = KubernetesSecretService(namespace, secret_name)

    await secret.create_or_replace(data)


@activity.defn
async def create_dns_activity(veritable: VeritableSpec) -> None:
    """
    :return:
    """
    config: AppSettings = get_settings()

    domain_name: str = config.product_config.get("veritable").domain_name

    google_dns = GoogleDNS(
        cname=f"{config.google_dns_cname}.",
        fqdn=f"{veritable.tenant}.{domain_name}.",
        zone_name="veritableapp"
    )

    # create dns
    google_dns.create_dns()

    # check dns propagation
    google_dns.check_dns_propagation_cf()


@activity.defn
async def deploy_veritable_ui_activity(veritable: VeritableSpec) -> None:
    """
    :return:
    """
    config: AppSettings = get_settings()

    domain_name: str = config.product_config.get("veritable").domain_name
    repo_name = "veritable-ui"

    deploy_ui(
        environment=veritable.environment,
        tenant=veritable.tenant,
        image_tag=veritable.imageTag,
        domain_name=domain_name,
        repo_name=repo_name
    )

    logger.info(f"Deployed Veritable UI for {veritable.tenant}")


@activity.defn
async def create_realm_activity(veritable: VeritableSpec) -> None:
    """
    :return:
    """

    tenant_url = f"{veritable.tenant}.veritable.app" \
        if veritable.environment == "production" else f"{veritable.tenant}.int.veritable.app"

    payload: dict = {
        "product": "veritable",
        "tenant": veritable.tenant,
        "realm_name": f"veritable_{veritable.tenant}",
        "domain_org": "app",
        "tenant_url": tenant_url,
        "customer_username": veritable.customerUserName,
        "customer_email": veritable.customerEmail,
        "admin_user": "admin",
        "admin_email": "practifly-be@314ecorp.com",
        "customer_realm_roles":  veritable.customerRealmRoles
    }
    workflow_id = (
        f"keycloak_realm_creation_workflow_veritable-{veritable.environment}-{veritable.tenant}"
    )

    # trigger keycloak realm creation workflow
    await trigger_keycloak_realm_creation_workflow(payload=payload, workflow_id=workflow_id)

    # check workflow status and wait for completion
    workflow_status = await check_workflow_status(workflow_id)

    # wait for workflow to complete
    while workflow_status != WorkflowExecutionStatus.COMPLETED.name:

        if workflow_status in (
                WorkflowExecutionStatus.FAILED.name,
                WorkflowExecutionStatus.CANCELED.name,
                WorkflowExecutionStatus.TERMINATED.name,
        ):
            logger.error(f"Keycloak realm creation workflow {workflow_status} for {workflow_id}")
            raise Exception(f"Keycloak realm creation workflow {workflow_status} for {workflow_id}")

        time.sleep(5)
        workflow_status = await check_workflow_status(workflow_id)

    logger.info(f"Keycloak realm creation workflow completed for {workflow_id}")


# todo update this function
async def check_pod_logs(namespace: str, job_name: str):
    """
    :return:

    """
    k8s_config.load_kube_config()
    try:
        v1 = client.CoreV1Api()
        pod_list = v1.list_namespaced_pod(namespace=namespace, label_selector=f"job-name={job_name}")
        for pod in pod_list.items:
            if pod.status.phase == "Running":
                pod_name = pod.metadata.name
                container_name = pod.spec.containers[0].name
                response = v1.read_namespaced_pod_log(name=pod_name, namespace=namespace, container=container_name)
                logger.info(f"Pod logs for {pod_name}: {response}")
    except ApiException as e:
        logger.error(f"Error getting pod logs: {e}")
        raise e


@dataclass
class ProvisioningJobInput:
    veritable: VeritableSpec
    postgres_user: str


@activity.defn
async def provisioning_job_activity(veritable: VeritableSpec) -> None:
    """
    :return:
    """
    postgres_user = f"veritable_{veritable.tenant}"

    config: AppSettings = get_settings()

    product_config: ProductConfig = config.product_config.get("veritable")

    postgres_password = OnePasswordUtil(
        tenant=veritable.tenant,
        server_item=product_config.one_password_server_item,
        vault=product_config.vault_name
    ).get_key("postgres_database_password")

    logger.info(f"Provisioning job activity for {veritable.tenant}")

    job_name = "veritable-tenant-provisioning-job"
    job_type = "provisioning"

    job_body: client.V1Job = client.V1Job(
        api_version="batch/v1",
        metadata=client.V1ObjectMeta(
            name=job_name,
            namespace=veritable.tenant,
            labels={"app": "veritable", "jobKind": job_type},
            annotations={"app": "veritable", "jobKind": job_type}
        ),
        spec=client.V1JobSpec(
            template=client.V1JobTemplateSpec(
                spec=client.V1PodSpec(
                    image_pull_secrets=[client.V1LocalObjectReference(name="registrycred")],
                    containers=[
                        client.V1Container(
                            name=job_name,
                            env=[
                                client.V1EnvVar(
                                    name="POSTGRES__PASSWORD",
                                    value=postgres_password
                                ),
                                client.V1EnvVar(
                                    name="POSTGRES__USER",
                                    value=postgres_user
                                ),
                                client.V1EnvVar(
                                    name="RELEASE_VERSION",
                                    value=veritable.imageTag
                                ),
                                client.V1EnvVar(
                                    name="PROVISIONING_CONFIG",
                                    value="/provisioningConfig/provisioning-config.json"
                                )
                            ],
                            volume_mounts=[
                                client.V1VolumeMount(
                                    name="veritable-provisioning-config",
                                    mount_path="/provisioningConfig",
                                    read_only=True
                                )
                            ],
                            image=f"registry.314ecorp.tech/veritable-server:{veritable.imageTag}",
                            command=["/bin/sh", "-c"],
                            args=[
                                f"cd /app && python3 /app/provisioning/{job_type}_.py "
                                f"--config /provisioningConfig/provisioning-config.json"
                            ],
                        )
                    ],
                    volumes=[
                        client.V1Volume(
                            name="veritable-provisioning-config",
                            config_map=client.V1ConfigMapVolumeSource(
                                name="veritable-provisioning-config",
                                items=[client.V1KeyToPath(
                                    key="provisioning-config.json",
                                    path="provisioning-config.json")
                                ],
                            )
                        )
                    ],
                    restart_policy="Never",
                )
            )
        )
    )

    # create job
    kubernetes_job = KubernetesJob(
        namespace=veritable.tenant,
        job_name=f"veritable-tenant-provisioning-job",
    )

    await kubernetes_job.create_or_replace_job(job_body)

    # check job execution status
    counter = 0
    while True:
        status: client.V1JobStatus = await kubernetes_job.get_job_execution_status()
        if status is not None and status.completion_time is not None:
            logger.info(f"Job execution completed for {veritable.tenant}")
            await check_pod_logs(namespace=veritable.tenant, job_name=job_name)
            break
        elif counter == 60:
            logger.error(f"Provisioning Job execution timed out for {veritable.tenant}")
            raise Exception(f"Provisioning Job execution timed out for {veritable.tenant}")

        logger.info("Waiting for job execution to complete")
        time.sleep(60)
        counter += 1

    # delete job after completion
    await kubernetes_job.delete_job()

@activity.defn
async def create_k8s_service_activity(
    veritable: VeritableSpec,
) -> None:
    """
    :return:
    """

    k8s_service = KubernetesService(
        namespace=veritable.tenant,
        product_name="veritable",
    )

    await k8s_service.create_or_replace(port=8000)


@activity.defn
async def create_virtual_service_activity(
    veritable: VeritableSpec,
) -> None:
    """
    :return:
    """
    config: AppSettings = get_settings()
    product_config: ProductConfig = config.product_config.get("veritable")

    istio_virtual_service = IstioVirtualService(
        namespace=veritable.tenant,
        product="veritable",
    )

    http_list = []

    # http_api router
    http_api = {
        "name": "veritable-api",
        "route": [{
            "destination": {
                "host": f"veritable.{veritable.tenant}.svc.cluster.local",
                "port": {"number": 8000},
                "headers": {
                    "response": {
                        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
                    }
                }
            }
        }],
        "match": [
            {"uri": {"regex": "^/api/v1/.*"}},
            {"uri": {"regex": "^/public/api/v1/.*"}},
            {"uri": {"prefix": "/docs"}},
            {"uri": {"prefix": "/redoc"}},
        ]
    }
    http_list.append(http_api)

    # http_redirect router
    if veritable.environment != "production":
        http_redirect = {
            "name": "redirect",
            "match": [{
                "uri": {"exact": "/"},
            }],
            "redirect": {
               "uri": f"/{veritable.imageTag}/"
            }
        }
        http_list.append(http_redirect)

    # http_ui router
    http_ui = {
        "name": "veritable-ui",
        "route": [{
            "destination": {
                "host": f"varnish-svc.varnish.svc.cluster.local",
                "port": {"number": 80},

            }
        }],
        "match": [{
            "uri": {"prefix": "/"},
        }]
    }
    http_list.append(http_ui)

    job_body = {
        "apiVersion": "networking.istio.io/v1beta1",
        "kind": "VirtualService",
        "metadata": {
            "name": "veritable-vs",
            "namespace": veritable.tenant,
        },
        "spec": {
            "hosts": [
                f"{veritable.tenant}.{product_config.domain_name}"
            ],
            "gateways": ["istio-system/istiogateway"],
            "http": http_list
        }
    }

    await istio_virtual_service.create_or_replace(job_body)


@activity.defn
async def create_deployment_activity(
    veritable: VeritableSpec,
) -> None:
    """
    :return:
    """
    logger.info(f"Deployment activity for {veritable.tenant}")

    product_config: ProductConfig = get_settings().product_config.get("veritable")

    postgres_user = f"veritable_{veritable.tenant}"
    postgres_password = OnePasswordUtil(
        tenant=veritable.tenant,
        server_item=product_config.one_password_server_item,
        vault=product_config.vault_name
    ).get_key("postgres_database_password")

    # create server deployment
    k8s_deployment = DeploymentJob(
        namespace=veritable.tenant,
        deployment_name=f"veritable",
        product_name="veritable",
    )

    server_deployment_body: client.V1Deployment = client.V1Deployment(
        kind="Deployment",
        metadata=client.V1ObjectMeta(
            name=f"veritable",
            namespace=veritable.tenant,
        ),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(
                match_labels={"app": "veritable"}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={"app": "veritable"}
                ),
                spec=client.V1PodSpec(
                    image_pull_secrets=[client.V1LocalObjectReference(name="registrycred")],
                    node_selector={"app": "314e"},
                    containers=[
                        client.V1Container(
                            name="veritable",
                            image=f"registry.314ecorp.tech/veritable-server:{veritable.imageTag}",
                            resources=client.V1ResourceRequirements(
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
                                client.V1ContainerPort(
                                    name="http",
                                    protocol="TCP",
                                    container_port=8000
                                )
                            ],
                            image_pull_policy="Always",
                            volume_mounts=[
                                client.V1VolumeMount(
                                    name="env-volume",
                                    mount_path="/config/env-config.json",
                                    sub_path="env-config.json"
                                ),
                                client.V1VolumeMount(
                                    name="tenant-volume",
                                    mount_path="/config/tenant-config.json",
                                    sub_path="tenant-config.json"
                                )
                            ],
                            env=[
                                client.V1EnvVar(
                                    name="DEPLOYMENT",
                                    value=veritable.environment
                                ),
                                client.V1EnvVar(
                                    name="POSTGRES__PASSWORD",
                                    value=postgres_password
                                ),
                                client.V1EnvVar(
                                    name="POSTGRES__USER",
                                    value=postgres_user
                                ),
                                client.V1EnvVar(
                                    name="RELEASE_VERSION",
                                    value=veritable.imageTag,
                                ),
                                client.V1EnvVar(
                                    name="APP_CONFIG_DIR",
                                    value="/config"
                                ),
                                client.V1EnvVar(
                                    name="CLIENT_CODE",
                                    value=veritable.tenant
                                ),
                                client.V1EnvVar(
                                    name="IS_CLI",
                                    value="FALSE"
                                ),
                                client.V1EnvVar(
                                    name="ORG_NAME",
                                    value=veritable.orgName
                                )
                            ]
                        )
                    ],
                    volumes=[
                        client.V1Volume(
                            name="env-volume",
                            config_map=client.V1ConfigMapVolumeSource(
                                name="veritable-env-config",
                                items=[client.V1KeyToPath(key="env-config.json", path="env-config.json")]
                            )
                        ),
                        client.V1Volume(
                            name="tenant-volume",
                            config_map=client.V1ConfigMapVolumeSource(
                                name="veritable-tenant-config",
                                items=[client.V1KeyToPath(key="veritable-tenant-config", path="tenant-config.json")]
                            )
                        ),
                        client.V1Volume(
                            name="provisioning-volume",
                            config_map=client.V1ConfigMapVolumeSource(
                                name="veritable-provisioning-config",
                                items=[client.V1KeyToPath(
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

    # create cli deployment

    cli_deployment_body: client.V1Deployment = client.V1Deployment(
        kind="Deployment",
        metadata=client.V1ObjectMeta(
            name=f"veritable-cli",
            namespace=veritable.tenant,
        ),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(
                match_labels={"app": "veritable-cli"}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={"app": "veritable-cli"}
                ),
                spec=client.V1PodSpec(
                    image_pull_secrets=[client.V1LocalObjectReference(name="registrycred")],
                    node_selector={"app": "314e"},
                    containers=[
                        client.V1Container(
                            name="veritable",
                            image=f"registry.314ecorp.tech/veritable-server:{veritable.imageTag}",
                            resources=client.V1ResourceRequirements(
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
                                client.V1ContainerPort(
                                    name="http",
                                    protocol="TCP",
                                    container_port=8000
                                )
                            ],
                            image_pull_policy="Always",
                            volume_mounts=[
                                client.V1VolumeMount(
                                    name="env-volume",
                                    mount_path="/config/env-config.json",
                                    sub_path="env-config.json"
                                ),
                                client.V1VolumeMount(
                                    name="tenant-volume",
                                    mount_path="/config/tenant-config.json",
                                    sub_path="tenant-config.json"
                                ),
                                client.V1VolumeMount(
                                    name="vector-volume",
                                    mount_path="/vector",
                                    read_only=True
                                ),
                                client.V1VolumeMount(
                                    name="veritable-pvc",
                                    mount_path="/data",
                                    read_only=False
                                )
                            ],
                            env=[
                                client.V1EnvVar(
                                    name="DEPLOYMENT",
                                    value=veritable.environment
                                ),
                                client.V1EnvVar(
                                    name="POSTGRES__PASSWORD",
                                    value=postgres_password
                                ),
                                client.V1EnvVar(
                                    name="POSTGRES__USER",
                                    value=postgres_user
                                ),
                                client.V1EnvVar(
                                    name="RELEASE_VERSION",
                                    value=veritable.imageTag,
                                ),
                                client.V1EnvVar(
                                    name="APP_CONFIG_DIR",
                                    value="/config"
                                ),
                                client.V1EnvVar(
                                    name="CLIENT_CODE",
                                    value=veritable.tenant
                                ),
                                client.V1EnvVar(
                                    name="IS_CLI",
                                    value="TRUE"
                                ),
                                client.V1EnvVar(
                                    name="ORG_NAME",
                                    value=veritable.orgName
                                )
                            ]
                        )
                    ],
                    volumes=[
                        client.V1Volume(
                            name="env-volume",
                            config_map=client.V1ConfigMapVolumeSource(
                                name="veritable-env-config",
                                items=[client.V1KeyToPath(key="env-config.json", path="env-config.json")]
                            )
                        ),
                        client.V1Volume(
                            name="tenant-volume",
                            config_map=client.V1ConfigMapVolumeSource(
                                name="veritable-tenant-config",
                                items=[client.V1KeyToPath(key="veritable-tenant-config", path="tenant-config.json")]
                            )
                        ),
                        client.V1Volume(
                            name="vector-volume",
                            config_map=client.V1ConfigMapVolumeSource(
                                name="veritable-cli-vector-config",
                                items=[client.V1KeyToPath(key="vector-config.toml", path="vector-config.toml")]
                            )
                        ),
                        client.V1Volume(
                            name="veritable-pvc",
                            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
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
        deployment_name=f"veritable-cli",
        product_name="veritable",
    )

    await k8s_deployment.create_or_replace(cli_deployment_body)


@activity.defn
async def vm_pod_scraper_activity(veritable: VeritableSpec) -> None:
    """
    :return:
    """
    logger.info(f"VM Pod Scraper activity for {veritable.tenant}")

    # create VM Pod Scrapper for server

    vms_spec = {
        "namespaceSelector": {
            "matchNames": [veritable.tenant]
        },
        "podMetricsEndpoints": [{
            "path": "/metrics",
            "port": "http",
            "interval": "5s",
        }],
        "selector": {
            "matchLabels": {
                "app": "veritable"
            }
        }
    }

    server_body = {
        "apiVersion": "operator.victoriametrics.com/v1beta1",
        "kind": "VMPodScrape",
        "metadata": {
            "name": "veritable-metrics",
            "namespace": veritable.tenant,
        },
        "spec": vms_spec
    }

    VMPodScrapper(
        namespace=veritable.tenant,
        name="veritable-metrics"
    ).create_or_replace(server_body)

    # create VM Pod Scrapper for cli

    cli_vms_spec = {
        "namespaceSelector": {
            "matchNames": [veritable.tenant]
        },
        "podMetricsEndpoints": [{
            "path": "/metrics",
            "port": "http",
            "interval": "5s",
        }],
        "selector": {
            "matchLabels": {
                "app": "veritable-cli"
            }
        }
    }

    cli_body = {
        "apiVersion": "operator.victoriametrics.com/v1beta1",
        "kind": "VMPodScrape",
        "metadata": {
            "name": "veritable-cli-metrics",
            "namespace": veritable.tenant,
        },
        "spec": cli_vms_spec
    }

    VMPodScrapper(
        namespace=veritable.tenant,
        name="veritable-cli-metrics"
    ).create_or_replace(cli_body)

    logger.info(f"VM Pod Scraper created for {veritable.tenant}")


def convert_to_binary(input_string):
    binary_string = ''.join(format(ord(c), '08b') for c in input_string)
    binary_number = int(binary_string, 2)
    return binary_number


@activity.defn
async def create_grafana_alerts_activity(veritable: VeritableSpec) -> None:
    """
    :return:
    """
    logger.info(f"Create Grafana alerts for {veritable.tenant}")

    product_config: ProductConfig = get_settings().product_config.get("veritable")

    worker_beat_panel_id = str(convert_to_binary(veritable.tenant))
    server_panel_id = "1" + worker_beat_panel_id
    worker_count_panel_id = "2" + worker_beat_panel_id

    # create grafana panels
    grafana_utils = GrafanaUtils()
    current_dashboard = grafana_utils.get_dashboard(dashboard_uid=product_config.grafana.dashboard_uid)

    current_panels = current_dashboard.get("dashboard", {}).get("panels", [])

    modified_panels = []
    template_env = get_env("veritable")
    # grafana worker beat panel
    worker_beat_panel_template = template_env.get_template("grafana_worker_beat_pannel.json")
    worker_beat_panel = worker_beat_panel_template.render(
        tenant=veritable.tenant, PanelID=worker_beat_panel_id, DatasourceUID=product_config.grafana.datasource_uid
    )
    modified_panels.append(orjson.loads(worker_beat_panel))

    # grafana worker count pannel
    worker_count_panel_template = template_env.get_template("grafana_worker_count_pannel.json")
    worker_count_panel = worker_count_panel_template.render(
        tenant=veritable.tenant, PanelID=worker_count_panel_id, DatasourceUID=product_config.grafana.datasource_uid
    )
    modified_panels.append(orjson.loads(worker_count_panel))

    # grafana server pannel
    server_panel_template = template_env.get_template("grafana_server_pannel.json")
    server_panel = server_panel_template.render(
        tenant=veritable.tenant, PanelID=server_panel_id, DatasourceUID=product_config.grafana.datasource_uid
    )
    modified_panels.append(orjson.loads(server_panel))

    new_panels = [
        panel for panel in current_panels
        if panel.get("title") not in [new_element.get("title") for new_element in modified_panels]
    ]

    new_panels.extend(modified_panels)

    current_dashboard["dashboard"]["panels"] = new_panels

    grafana_utils.update_dashboard(dashboard_json=current_dashboard)

    logger.info(f"Grafana Panels created for {veritable.tenant}")

    # Alert for worker beat
    worker_beat_alert_template = template_env.get_template("grafana_worker_beat_alerts.json")
    worker_beat_alert = worker_beat_alert_template.render(
        tenant=veritable.tenant, DatasourceUID=product_config.grafana.datasource_uid, PannelID=worker_beat_panel_id,
        FolderUID=product_config.grafana.alert_folder_uid, DashboardUID=product_config.grafana.dashboard_uid
    )
    grafana_utils.create_alerts(orjson.loads(worker_beat_alert))

    # Alert for worker count
    worker_count_alert_template = template_env.get_template("grafana_worker_count_alerts.json")
    worker_count_alert = worker_count_alert_template.render(
        tenant=veritable.tenant, DatasourceUID=product_config.grafana.datasource_uid, PannelID=worker_count_panel_id,
        FolderUID=product_config.grafana.alert_folder_uid, DashboardUID=product_config.grafana.dashboard_uid
    )
    grafana_utils.create_alerts(orjson.loads(worker_count_alert))

    # Alert for server
    server_alert_template = template_env.get_template("grafana_server_alerts.json")
    server_alert = server_alert_template.render(
        tenant=veritable.tenant, DatasourceUID=product_config.grafana.datasource_uid, PannelID=server_panel_id,
        FolderUID=product_config.grafana.alert_folder_uid, DashboardUID=product_config.grafana.dashboard_uid
    )
    grafana_utils.create_alerts(orjson.loads(server_alert))

    logger.info(f"Grafana Alerts created for {veritable.tenant}")
