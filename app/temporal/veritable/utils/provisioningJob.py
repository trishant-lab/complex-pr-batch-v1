import os
import time

from kubernetes import client as k8s_client, config as k8s_config
from kubernetes.client import ApiException
from loguru import logger

from app.onepasswordutil import OnePasswordUtil
from app.temporal.common.kubernetesJob import KubernetesJob
from app.temporal.veritable.utils.common import VeritableSpec, OnepasswordItemName, OnepasswordVaultName, ProductName


async def check_pod_logs(namespace: str, job_name: str):
    """
    :return:

    """
    k8s_config.load_kube_config()
    provisioning_log = f"{namespace.lower()} Provisioning succeeded!"
    try:
        v1 = k8s_client.CoreV1Api()
        pod_list = v1.list_namespaced_pod(namespace=namespace, label_selector=f"job-name={job_name}")

        if not pod_list.items:
            logger.error(f"No pods found for job {job_name}")
            return False

        # sort the pod list by creation time in reverse order
        pod_list.items.sort(key=lambda x: x.metadata.creation_timestamp, reverse=True)

        pod = pod_list.items[0]

        pod_name = pod.metadata.name
        logs = v1.read_namespaced_pod_log(name=pod_name, namespace=namespace)

        if not logs.__contains__(provisioning_log):
            logger.error(f"Provisioning failed for {namespace}: {logs}")
            return False

        return True

    except ApiException as e:
        logger.error(f"Error getting pod logs: {e}")
        raise e


async def check_execution_status(veritable: VeritableSpec, kubernetes_job: KubernetesJob, job_name: str):
    """
    :return:
    """
    counter = 0
    while True:
        status: k8s_client.V1JobStatus = await kubernetes_job.get_job_execution_status()
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

    job_body: k8s_client.V1Job = k8s_client.V1Job(
        api_version="batch/v1",
        metadata=k8s_client.V1ObjectMeta(
            name=job_name,
            namespace=veritable.tenant,
            labels={"app": ProductName, "jobKind": job_type},
            annotations={"app": ProductName, "jobKind": job_type}
        ),
        spec=k8s_client.V1JobSpec(
            template=k8s_client.V1JobTemplateSpec(
                spec=k8s_client.V1PodSpec(
                    image_pull_secrets=[k8s_client.V1LocalObjectReference(name="registrycred")],
                    containers=[
                        k8s_client.V1Container(
                            name=job_name,
                            env=[
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
                                    value=veritable.imageTag
                                ),
                                k8s_client.V1EnvVar(
                                    name="PROVISIONING_CONFIG",
                                    value="/provisioningConfig/provisioning-config.json"
                                )
                            ],
                            volume_mounts=[
                                k8s_client.V1VolumeMount(
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
                        k8s_client.V1Volume(
                            name="veritable-provisioning-config",
                            config_map=k8s_client.V1ConfigMapVolumeSource(
                                name="veritable-provisioning-config",
                                items=[k8s_client.V1KeyToPath(
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
    if not await check_execution_status(veritable, kubernetes_job, job_name):
        await kubernetes_job.delete_job()
        raise Exception(f"Provisioning Job execution failed for {veritable.tenant}")
