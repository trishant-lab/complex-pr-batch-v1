import asyncio

from kubernetes import client as api_client
from kubernetes.client import V1Job, V1JobSpec, V1JobTemplateSpec, V1PodSpec, \
    V1LocalObjectReference, V1Container, V1EnvVar, V1VolumeMount, V1Volume, V1ConfigMapVolumeSource, V1KeyToPath, \
    V1EnvVarSource, V1SecretKeySelector
from kubernetes.client import V1ObjectMeta
from kubernetes.dynamic import Resource, ResourceField
from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.veritable.veritable import ProductName
from app.cli.veritable.models.veritableSpec import VeritableSpec
from app.core.settings import get_settings


def check_pod_logs(namespace: str, job_name: str):
    """
    :return:

    """
    provisioning_log = f"{namespace.lower()} Provisioning succeeded!"

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
        status: ResourceField = get_job_status(namespace=veritable.tenant, job_name=job_name)
        if status is not None and status.get("completionTime") is not None:
            logger.info(f"Job execution completed for {veritable.tenant}")
            return check_pod_logs(namespace=veritable.tenant, job_name=job_name)
        elif counter == 60:
            logger.error(f"Provisioning Job execution timed out for {veritable.tenant}")
            raise Exception(f"Provisioning Job execution timed out for {veritable.tenant}")

        logger.info("Waiting for job execution to complete")
        await asyncio.sleep(30)
        counter += 1


class ProvisioningJob(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self, veritable: VeritableSpec) -> None:
        self.veritable: VeritableSpec = veritable
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Job, api_version="v1"
        )
        self.env = get_settings().env
        self.job_name = "veritable-tenant-provisioning-job"
        self.job_type = "provisioning"
        self.postgres_user = f"veritable_{veritable.tenant}"

    def payload(self):
        body = V1Job(
            api_version="batch/v1",
            kind=ResourceKindEnum.Job.value,
            metadata=V1ObjectMeta(
                name=self.job_name,
                namespace=self.veritable.tenant,
                labels={"app": ProductName, "jobKind": self.job_type},
                annotations={"app": ProductName, "jobKind": self.job_type}
            ),
            spec=V1JobSpec(
                template=V1JobTemplateSpec(
                    spec=V1PodSpec(
                        image_pull_secrets=[V1LocalObjectReference(name="registrycred")],
                        containers=[
                            V1Container(
                                name=self.job_name,
                                env=[
                                    V1EnvVar(
                                        name="POSTGRES__PASSWORD",
                                        value_from=V1EnvVarSource(
                                            secret_key_ref=V1SecretKeySelector(
                                                key="password",
                                                name="veritable-postgres"
                                            )
                                        )
                                    ),
                                    V1EnvVar(name="POSTGRES__USER", value=self.postgres_user),
                                    V1EnvVar(name="RELEASE_VERSION", value=self.veritable.imageTag),
                                    V1EnvVar(name="PROVISIONING_CONFIG", value="/provisioningConfig/provisioning-config.json") # noqa
                                ],
                                volume_mounts=[
                                    V1VolumeMount(
                                        name="veritable-provisioning-config",
                                        mount_path="/provisioningConfig",
                                        read_only=True
                                    )
                                ],
                                image=f"registry.314ecorp.tech/veritable-server:{self.veritable.imageTag}",
                                command=["/bin/sh", "-c"],
                                args=[
                                    f"cd /app && python3 /app/provisioning/{self.job_type}_.py "
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

        job_body = self.k8s_dynamic_client.client.sanitize_for_serialization(body)
        return job_body

    async def put(self):
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource,
            body=self.payload(),
            field_manager="kubectl-client-side-apply"
        )
        if not await check_execution_status(self.veritable, self.job_name):
            self.k8s_dynamic_client.delete(resource=self.resource, name=self.job_name, namespace=self.veritable.tenant)
            raise Exception(f"Provisioning Job execution failed for {self.veritable.tenant}")

    def delete(self):
        try:
            self.k8s_dynamic_client.delete(
                resource=self.resource,
                name=self.job_name,
                namespace=self.veritable.tenant
            )
        except NotFoundError as e:
            logger.error(f"Provisioning job not found for {self.veritable.tenant}")
