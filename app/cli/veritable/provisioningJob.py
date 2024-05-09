import os
import time

from kubernetes import client as api_client
from kubernetes.client import V1Job, V1ObjectMeta, V1JobSpec, V1JobTemplateSpec, V1PodSpec, \
    V1LocalObjectReference, V1Container, V1EnvVar, V1VolumeMount, V1Volume, V1ConfigMapVolumeSource, V1KeyToPath, \
    V1JobStatus
from kubernetes.dynamic import Resource
from loguru import logger

from app.cli.k8s_util import get_dynamic_client, ResourceKindEnum, get_resource
from app.cli.veritable.common import VeritableSpec, OnepasswordItemName, OnepasswordVaultName, ProductName
from app.onepasswordutil import OnePasswordUtil


async def check_pod_logs(namespace: str, job_name: str):
    """
    :return:

    """
    provisioning_log = f"{namespace.lower()} Provisioning succeeded!"

    k8s_dynamic_client = get_dynamic_client()
    resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Pod, api_version="v1")
    pod = k8s_dynamic_client.get(resource=resource, name=job_name, namespace=namespace)

    if not pod.items:
        logger.error(f"No pods found for job {job_name}")
        return False

    # sort the pod list by creation time in reverse order
    pod.items.sort(key=lambda x: x.metadata.creation_timestamp, reverse=True)

    pod = pod.items[0]
    pod_name = pod.metadata.name

    core_v1_api = api_client.CoreV1Api(k8s_dynamic_client)
    logs = core_v1_api.read_namespaced_pod_log(name=pod_name, namespace=namespace)

    if not logs.__contains__(provisioning_log):
        logger.error(f"Provisioning failed for {namespace}: {logs}")
        return False

    return True


def get_job_status(namespace: str, job_name: str) -> V1JobStatus:
    dynamic_client = get_dynamic_client()
    resource: Resource = get_resource(dynamic_client=dynamic_client, kind=ResourceKindEnum.Job, api_version="batch/v1")
    job = dynamic_client.get(resource=resource, name=job_name, namespace=namespace)
    return job.status


async def check_execution_status(veritable: VeritableSpec, job_name: str):
    """
    :return:
    """
    counter = 0
    while True:
        status: V1JobStatus = get_job_status(namespace=veritable.tenant, job_name=job_name)
        if status is not None and status.completion_time is not None:
            logger.info(f"Job execution completed for {veritable.tenant}")
            return await check_pod_logs(namespace=veritable.tenant, job_name=job_name)
        elif counter == 60:
            logger.error(f"Provisioning Job execution timed out for {veritable.tenant}")
            raise Exception(f"Provisioning Job execution timed out for {veritable.tenant}")

        logger.info("Waiting for job execution to complete")
        time.sleep(5)
        counter += 1


async def provisioning_job(veritable: VeritableSpec):
    """
    Provisioning Job
    """

    postgres_user = f"veritable_{veritable.tenant}"
    environment = os.getenv("DEPLOYMENT", "integration").lower()

    postgres_password = OnePasswordUtil(
        tenant=veritable.tenant,
        server_item=OnepasswordItemName.format(environment=environment),
        vault=OnepasswordVaultName
    ).get_key("postgres_database_password")

    logger.info(f"Provisioning job activity for {veritable.tenant}")

    job_name = "veritable-tenant-provisioning-job"
    job_type = "provisioning"

    job_body: V1Job = V1Job(
        api_version="v1",
        metadata=V1ObjectMeta(
            name=job_name,
            namespace=veritable.tenant,
            labels={"app": ProductName, "jobKind": job_type},
            annotations={"app": ProductName, "jobKind": job_type}
        ),
        spec=V1JobSpec(
            template=V1JobTemplateSpec(
                spec=V1PodSpec(
                    image_pull_secrets=[V1LocalObjectReference(name="registrycred")],
                    containers=[
                        V1Container(
                            name=job_name,
                            env=[
                                V1EnvVar(name="POSTGRES__PASSWORD", value=postgres_password),
                                V1EnvVar(name="POSTGRES__USER", value=postgres_user),
                                V1EnvVar(name="RELEASE_VERSION", value=veritable.imageTag),
                                V1EnvVar(name="PROVISIONING_CONFIG", value="/provisioningConfig/provisioning-config.json") # noqa
                            ],
                            volume_mounts=[
                                V1VolumeMount(
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
                        V1Volume(
                            name="veritable-provisioning-config",
                            config_map=V1ConfigMapVolumeSource(
                                name="veritable-provisioning-config",
                                items=[V1KeyToPath(
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

    k8s_dynamic_client = get_dynamic_client()
    resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Job, api_version="v1")

    body = k8s_dynamic_client.client.sanitize_for_serialization(job_body)

    k8s_dynamic_client.server_side_apply(resource=resource, body=body, field_manager="kubectl-client-side-apply")

    # check job execution status
    if not await check_execution_status(veritable, job_name):
        k8s_dynamic_client.delete(resource=resource, name=job_name, namespace=veritable.tenant)
        raise Exception(f"Provisioning Job execution failed for {veritable.tenant}")


async def delete_provisioning_job(tenant_name: str):
    """
    Delete provisioning job
    """

    dynamic_client = get_dynamic_client()
    resource = get_resource(dynamic_client=dynamic_client, kind=ResourceKindEnum.Job, api_version="batch/v1")
    dynamic_client.delete(resource=resource, name="veritable-tenant-provisioning-job", namespace=tenant_name)
    logger.info(f"Deleted provisioning job for {tenant_name}")
