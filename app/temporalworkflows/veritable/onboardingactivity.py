import asyncio
from dataclasses import dataclass
from tempfile import TemporaryDirectory

from cryptography.fernet import Fernet
from kubernetes import client
from loguru import logger
from temporalio import activity

from temporalio.client import WorkflowExecutionStatus

from app.core.settings import AppSettings, get_settings, ProductConfig
from app.temporalworkflows.common.GoogleDNS import GoogleDNS
from app.temporalworkflows.common.configmap import ConfigMap
from app.temporalworkflows.common.deployment import DeploymentJob
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
        "database_password": ""
    }
    workflow_id = f"{payload.get('product')}-{payload.get('env')}-{payload.get('tenant')}"
    await trigger_postgres_database_setup_workflow(payload, workflow_id)

    workflow_status = await check_workflow_status(workflow_id)

    # wait for workflow to complete
    while workflow_status != WorkflowExecutionStatus.COMPLETED.name:

        if workflow_status in (
                WorkflowExecutionStatus.FAILED.name,
                WorkflowExecutionStatus.CANCELED.name,
                WorkflowExecutionStatus.TERMINATED.name,
        ):
            logger.error(f"Postgres database setup workflow {workflow_status} for {workflow_id}")
            raise Exception(f"Postgres database setup workflow {workflow_status} for {workflow_id}")

        await asyncio.sleep(5)
        workflow_status = await check_workflow_status(workflow_id)

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
        ConfigMap(tenant=veritable.tenant).apply_config(
            name="tenant-config.json",
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

    with TemporaryDirectory as temp_dir:
        with open(f"{temp_dir}/integration-provisioning-config.tmpl.json", "w") as f:
            f.write(output)

        # inject secret into tenant-config.json from 1Password
        secret_inject(
            source_file_path=f"{temp_dir}/integration-provisioning-config.tmpl.json",
            destination_path=f"{temp_dir}/provisioning-config.json"
        )

        # apply configmap in k8s namespace
        ConfigMap(tenant=veritable.tenant).apply_config(
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

    with TemporaryDirectory as temp_dir:
        with open(f"{temp_dir}/integration-env-config.tmpl.json", "w") as f:
            f.write(output)

        # inject secret into tenant-config.json from 1Password
        secret_inject(
            source_file_path=f"{temp_dir}/integration-env-config.tmpl.json",
            destination_path=f"{temp_dir}/env-config.json"
        )

        # apply configmap in k8s namespace
        ConfigMap(tenant=veritable.tenant).apply_config(
            name="veritable-env-config",
            data={"env-config.json": open(f"{temp_dir}/env-config.json").read()}
        )


def apply_vector_config(veritable: VeritableSpec):
    """
    :return:

    """
    ConfigMap(tenant=veritable.tenant).apply_config(
        name="veritable-cli-vector-config",
        data={"vector-config.toml": "[log_schema]\nhost_key = \"host\"\nmessage_key = \"message\"\nsource_type_key = \"source_type\"\ntimestamp_key = \"timestamp\"\n\n# sources for logs\n\n[sources.custom_logs]\ntype = \"file\"\ninclude = [\"/var/log/supervisord/veritable_*\"]\nfingerprint.strategy = \"device_and_inode\"\n\n[sinks.vector_sink]\ntype = \"loki\"\ninputs = [ \"custom_logs\" ]\nendpoint = \"http://loki.monitoring-system.svc.cluster.local:3100\" \n[sinks.vector_sink.encoding]\ncodec = \"json\"\n[sinks.vector_sink.labels]\nname = \"veritable_custom_logs_" + veritable.tenant + "\""}  # noqa
    )


@activity.defn
async def create_configmap_activity(veritable: VeritableSpec) -> None:
    """
    Create configmap activity
    """

    # generate fernet key and insert into 1Password if not exists
    OnePasswordUtil(
        tenant=veritable.tenant,
        server_item=f"veritable-tenant-config-{veritable.environment}",
        vault="veritable"
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
    secret = KubernetesSecretService(namespace, secret_name, data)

    await secret.create_or_replace()


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
        zone_name="veritable-int"
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


@activity.defn
async def create_realm_activity(veritable: VeritableSpec) -> None:
    """
    :return:
    """

    payload: dict = {
        "product": "Veritable",
        "tenant": veritable.tenant,
        "realm_name": f"veritable_{veritable.tenant}",
        "env": veritable.environment,
        "domain_org": "app",
        "customer_username": veritable.customerUserName,
        "customer_email": veritable.customerEmail,
        "admin_user": "admin",
        "admin_email": "practifly-be@314ecorp.com",
        "customer_realm_roles":  veritable.customerRealmRoles
    }
    workflow_id = f"{payload.get('product')}-{payload.get('env')}-{payload.get('tenant')}"

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

        await asyncio.sleep(5)
        workflow_status = await check_workflow_status(workflow_id)

    logger.info(f"Keycloak realm creation workflow completed for {workflow_id}")


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

    product_config: ProductConfig = get_settings().product_config.get("veritable")

    postgres_password = OnePasswordUtil(
        tenant=veritable.tenant,
        server_item=product_config.one_password_server_item,
        vault=product_config.vault_name
    ).get_key("postgres_password")

    logger.info(f"Provisioning job activity for {veritable.tenant}")

    template_env = get_env("veritable")
    template = template_env.get_template("job.yaml")

    job_body = template.render(
        job_name=f"veritable-tenant-provisioning-job",
        tenant=veritable.tenant,
        job_kind="provisioning",
        image_tag=veritable.imageTag,
        postgres_password=postgres_password,
        postgres_user=postgres_user
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
            # todo check pod logs
            return
        elif counter == 60:
            logger.error(f"Provisioning Job execution timed out for {veritable.tenant}")
            raise Exception(f"Provisioning Job execution timed out for {veritable.tenant}")

        logger.info("Waiting for job execution to complete")
        await asyncio.sleep(5000)
        counter += 1


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
        port=8000
    )

    await k8s_service.create_or_replace()


@activity.defn
async def create_virtual_service_activity(
    veritable: VeritableSpec,
) -> None:
    """
    :return:
    """
    config: AppSettings = get_settings()

    istio_virtual_service = IstioVirtualService(
        namespace=veritable.tenant,
        product="veritable",
        environment=veritable.environment,
        domain_name=config.product_config.get("veritable").domain_name,
        image_tag=veritable.imageTag
    )

    template_env = get_env("veritable")
    template = template_env.get_template("istio_virtual_service.yaml")

    job_body = template.render(
        tenant=veritable.tenant,
        domain_name=config.product_config.get("veritable").domain_name,
        environment=veritable.environment,
        image_tag=veritable.imageTag
    )

    await istio_virtual_service.create_or_replace(job_body)


# def get_pod_spec(product_name: str, image_tag: str, port: int, environment: str, db_password: str):
#     return client.V1PodSpec(
#             image_pull_secrets=[client.V1LocalObjectReference(name="registrycred")],
#             node_selector={"app": "314e"},
#             containers=[
#                 client.V1Container(
#                     name=product_name,
#                     image=f"registry.314ecorp.tech/{image_tag}",
#                     # example: registry.314ecorp.tech/veritable-server:latest  # noqa
#                     resources=client.V1ResourceRequirements(
#                         requests={"cpu": "100m", "memory": "128Mi"},
#                         limits={"cpu": "500m", "memory": "512Mi"},
#                     ),
#                     ports=[
#                         client.V1ContainerPort(
#                             name="http",
#                             protocol="TCP",
#                             container_port=port
#                         )
#                     ],
#                     image_pull_policy="Always",
#                     volume_mounts=[
#                         client.V1VolumeMount(
#                             name="env-volume",
#                             mount_path="/config/env-config.json",
#                             sub_path="env-config.json"
#                         ),
#                         client.V1VolumeMount(
#                             name="tenant-volume",
#                             mount_path="/config/tenant-config.json",
#                             sub_path="tenant-config.json"
#                         )
#                     ],
#                     env=[
#                         client.V1EnvVar(
#                             name="DEPLOYMENT",
#                             value=environment
#                         ),
#                         client.V1EnvVar(
#                             name="POSTGRES__PASSWORD",
#                             value=db_password
#                         )
#                     ]
#                 )
#             ],
#             volumes=[
#                 client.V1Volume(
#                     name="env-volume",
#                     config_map=client.V1ConfigMapVolumeSource(
#                         name="veritable-env-config",
#                         items=[client.V1KeyToPath(key="env-config.json", path="env-config.json")]
#                     )
#                 ),
#             ]
#         )
#
#
# def get_deployment_template(product_name):
#     return client.V1PodTemplateSpec(
#             metadata=client.V1ObjectMeta(
#                 labels={"app": product_name}
#             ),
#         )


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
    ).get_key("postgres_password")

    template_env = get_env("veritable")

    # create server deployment
    server_deployment_template = template_env.get_template("server_deployment.yaml")

    server_deployment_body = server_deployment_template.render(
        replica=1,
        image_tag=veritable.imageTag,
        request={
            "cpu": veritable.serverSpec.request_cpu,
            "memory": veritable.serverSpec.request_memory
        },
        limit={
            "cpu": veritable.serverSpec.limit_cpu,
            "memory": veritable.serverSpec.limit_memory
        },
        container_port=8000,
        postgres_password=postgres_password,
        postgres_user=postgres_user,
        new_image_tag=veritable.newImageTag,
        tenant=veritable.tenant,
        org_name=veritable.orgName
    )

    # create deployment
    k8s_deployment = DeploymentJob(
        namespace=veritable.tenant,
        deployment_name=f"veritable-server",
        product_name="veritable",
        image_tag=veritable.imageTag,
        replicas=1,
    )

    await k8s_deployment.create_or_replace(server_deployment_body)

    # create cli deployment
    cli_deployment_template = template_env.get_template("cli_deployment.yaml")

    cli_deployment_body = cli_deployment_template.render(
        replica=1,
        image_tag=veritable.imageTag,
        request={
            "cpu": veritable.cliSpec.request_cpu,
            "memory": veritable.cliSpec.request_memory
        },
        limit={
            "cpu": veritable.cliSpec.limit_cpu,
            "memory": veritable.cliSpec.limit_memory
        },
        container_port=8000,
        postgres_password=postgres_password,
        postgres_user=postgres_user,
        new_image_tag=veritable.newImageTag,
        tenant=veritable.tenant,
        org_name=veritable.orgName
    )

    # create deployment
    k8s_deployment = DeploymentJob(
        namespace=veritable.tenant,
        deployment_name=f"veritable-cli",
        product_name="veritable",
        image_tag=veritable.imageTag,
        replicas=1,
    )

    await k8s_deployment.create_or_replace(cli_deployment_body)
