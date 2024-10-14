from kubernetes.client import (
    V1Job,
    V1ObjectMeta,
    V1JobSpec,
    V1JobTemplateSpec,
    V1PodSpec,
    V1LocalObjectReference,
    V1Container,
)
from kubernetes.dynamic.exceptions import NotFoundError

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.temporal.core.log import log_info, log_error
from app.core.settings import get_settings


class DatabaseMigrationJob(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(
        self: "DatabaseMigrationJob",
        tenant: str,
        product: str,
        job_name: str,
        postgres_user: str,
        postgres_password: str,
        docker_image: str,
        volume_mounts: list,
        volumes: list,
        container_envs: list,
    ) -> None:
        """
        Constructor
        """
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Job, api_version="v1"
        )
        self.env = get_settings().env
        self.job_name = job_name
        self.job_type = "atlas"
        self.tenant = tenant
        self.product = product
        self.postgres_user = postgres_user
        self.postgres_password = postgres_password
        self.docker_image = docker_image
        self.volume_mounts = volume_mounts
        self.volumes = volumes
        self.container_envs = container_envs

    def payload(self: "DatabaseMigrationJob") -> dict:
        """
        Job Payload
        """
        body = V1Job(
            api_version="batch/v1",
            kind=ResourceKindEnum.Job.value,
            metadata=V1ObjectMeta(
                namespace=self.tenant,
                name=self.job_name,
                labels={"app": self.product.lower(), "jobKind": self.job_type},
                annotations={"app": self.product.lower(), "jobKind": self.job_type},
            ),
            spec=V1JobSpec(
                template=V1JobTemplateSpec(
                    spec=V1PodSpec(
                        node_selector={"app": "314e"},
                        image_pull_secrets=[V1LocalObjectReference(name="registrycred")],
                        containers=[
                            V1Container(
                                name=self.job_name,
                                image=self.docker_image,
                                env=self.container_envs,
                                volume_mounts=self.volume_mounts,
                                command=["/bin/sh", "-c"],
                                args=["python3 /app/provisioning/atlas_migration.py"],
                            )
                        ],
                        volumes=self.volumes,
                        restart_policy="Never",
                    )
                )
            ),
        )

        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self: "DatabaseMigrationJob") -> None:
        """
        Put method
        """
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource, body=self.payload(), field_manager="kubectl-client-side-apply"
        )
        log_info(f"Atlas Job created for {self.tenant}")

    def delete(self: "DatabaseMigrationJob") -> None:
        """
        Delete method
        """
        try:
            self.k8s_dynamic_client.delete(resource=self.resource, name=self.job_name, namespace=self.tenant)
        except NotFoundError:
            log_error(f"Provisioning job not found for {self.tenant}")
