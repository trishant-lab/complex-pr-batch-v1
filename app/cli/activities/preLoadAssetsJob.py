import asyncio

from kubernetes.client import (
    V1Job,
    V1ObjectMeta,
    V1JobSpec,
    V1JobTemplateSpec,
    V1PodSpec,
    V1LocalObjectReference,
    V1Container,
    V1EnvVar,
    V1VolumeMount,
    V1Volume,
    V1ConfigMapVolumeSource,
    V1KeyToPath,
)
from kubernetes.dynamic import ResourceField, Resource
from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from kubernetes import client as api_client
from app.cli.temporal.jeeves.models.jeevesSpec import JeevesSpec
from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.temporal.core.log import log_info
from app.core.settings import get_settings
from app.onepasswordutil import OnePasswordUtil


def check_pod_logs(namespace: str, job_name: str) -> bool:
    """
    :return:

    """
    provisioning_log = f"Asset and Assignment preload job completed successfully for the tenant: {namespace}"

    k8s_dynamic_client = get_dynamic_client()
    resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Pod, api_version="v1")
    pods = k8s_dynamic_client.get(resource=resource, label_selector=f"job-name={job_name}", namespace=namespace)

    if not pods.items:
        logger.error(f"No pods found for job {job_name}")
        return False

    # sort the pod list by creation time in reverse order
    pods.items.sort(key=lambda x: x.metadata.creationTimestamp, reverse=True)

    pod = pods.items[0]
    pod_name = pod.metadata.name

    core_v1_api = api_client.CoreV1Api()
    logs = core_v1_api.read_namespaced_pod_log(name=pod_name, namespace=namespace)

    if not logs.__contains__(provisioning_log):
        logger.error(f"Provisioning failed for {namespace}: {logs}")
        return False

    return True


def get_job_status(namespace: str, job_name: str) -> ResourceField:
    """
    :return:
    """
    dynamic_client = get_dynamic_client()
    resource: Resource = get_resource(dynamic_client=dynamic_client, kind=ResourceKindEnum.Job, api_version="batch/v1")
    job = dynamic_client.get(resource=resource, name=job_name, namespace=namespace)
    return job.status


async def check_execution_status(jeeves: JeevesSpec, job_name: str) -> bool:
    """
    :return:
    """
    counter = 0
    while True:
        status: ResourceField = get_job_status(namespace=jeeves.tenant, job_name=job_name)
        if status is not None and status.get("completionTime") is not None:
            logger.info(f"Job execution completed for {jeeves.tenant}")
            return check_pod_logs(namespace=jeeves.tenant, job_name=job_name)
        elif counter == 60:
            logger.error(f"Provisioning Job execution timed out for {jeeves.tenant}")
            raise Exception(f"Provisioning Job execution timed out for {jeeves.tenant}")

        logger.info("Waiting for job execution to complete")
        await asyncio.sleep(30)
        counter += 1


class PreLoadAssetsJob(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self: "PreLoadAssetsJob", jeeves: JeevesSpec) -> None:
        """
        Constructor
        """
        self.jeeves: JeevesSpec = jeeves
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Job, api_version="v1"
        )
        self.env = get_settings().env
        self.job_name = "jeeves-preload-assets-job"
        self.job_type = "preload-assets"
        self.postgres_user = f"jeeves_{jeeves.tenant}"
        self.postgres_password = OnePasswordUtil(
            tenant=f"Jeeves_{jeeves.tenant}",
            server_item="application-config",
            vault="Jeeves",
        ).get_key("pg_password")
        self.image_tag = "production" if self.env == "production" else "sprint"

    def payload(self: "PreLoadAssetsJob") -> dict:
        """
        Job Payload
        """
        body = V1Job(
            api_version="batch/v1",
            kind=ResourceKindEnum.Job.value,
            metadata=V1ObjectMeta(
                namespace=self.jeeves.tenant,
                name=self.job_name,
                labels={"app": "jeeves", "jobKind": self.job_type},
                annotations={"app": "jeeves", "jobKind": self.job_type},
            ),
            spec=V1JobSpec(
                template=V1JobTemplateSpec(
                    spec=V1PodSpec(
                        node_selector={"app": "314e"},
                        image_pull_secrets=[V1LocalObjectReference(name="registrycred")],
                        containers=[
                            V1Container(
                                name=self.job_name,
                                image=f"registry.314ecorp.tech/jeeves-app:{self.image_tag}",
                                env=[
                                    V1EnvVar(name="POSTGRES_PASSWORD", value=self.postgres_password),
                                    V1EnvVar(name="POSTGRES_USER", value=self.postgres_user),
                                    V1EnvVar(name="APP_CONFIG_FILE", value="/config/tenant-config.json"),
                                    V1EnvVar(name="DEPLOYMENT", value=self.env),
                                    V1EnvVar(name="CLIENT_CODE", value=self.jeeves.tenant),
                                ],
                                volume_mounts=[
                                    V1VolumeMount(
                                        name="jeeves-tenant-config",
                                        mount_path="/config/tenant-config.json",
                                        sub_path="tenant-config.json",
                                        read_only=True,
                                    ),
                                    V1VolumeMount(
                                        name="rclone-volume", mount_path="/root/.config/rclone/", read_only=True
                                    ),
                                ],
                                command=["/bin/sh", "-c"],
                                args=[f"python3 /app/provisioning/preload_asset_and_assignment.py {self.jeeves.email}"],
                            )
                        ],
                        volumes=[
                            V1Volume(
                                name="rclone-volume",
                                config_map=V1ConfigMapVolumeSource(
                                    name="jeeves-rclone-config",
                                    items=[V1KeyToPath(key="rclone.conf", path="rclone.conf")],
                                ),
                            ),
                            V1Volume(
                                name="jeeves-tenant-config",
                                config_map=V1ConfigMapVolumeSource(
                                    name="jeeves-tenant-config",
                                    items=[V1KeyToPath(key="tenant-config.json", path="tenant-config.json")],
                                ),
                            ),
                        ],
                        restart_policy="Never",
                    )
                )
            ),
        )

        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    async def put(self: "PreLoadAssetsJob") -> None:
        """
        Put method
        """
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource, body=self.payload(), field_manager="kubectl-client-side-apply"
        )
        log_info(f"PreLoadAssetsJob Job created for {self.jeeves.tenant}")

        # await asyncio.sleep(300)
        if not await check_execution_status(self.jeeves, self.job_name):
            self.k8s_dynamic_client.delete(resource=self.resource, name=self.job_name, namespace=self.jeeves.tenant)
            raise Exception(f"Provisioning Job execution failed for {self.jeeves.tenant}")

    def delete(self: "PreLoadAssetsJob") -> None:
        """
        Delete method
        """
        try:
            self.k8s_dynamic_client.delete(resource=self.resource, name=self.job_name, namespace=self.jeeves.tenant)
        except NotFoundError:
            logger.error(f"Provisioning job not found for {self.jeeves.tenant}")
