from kubernetes.client import (
    V1Job,
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
    V1PersistentVolumeClaimVolumeSource,
)
from kubernetes.client import V1ObjectMeta
from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.jeeves.jeeves import JeevesSpec
from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.temporal.core.log import log_info
from app.core.settings import get_settings
from app.onepasswordutil import OnePasswordUtil


class AlembicJob(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self: "AlembicJob", jeeves: JeevesSpec) -> None:
        """
        Constructor
        """
        self.jeeves: JeevesSpec = jeeves
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Job, api_version="v1"
        )
        self.env = get_settings().env
        self.job_name = "jeeves-alembic-migration-job"
        self.job_type = "alembic"
        self.postgres_user = f"jeeves_{jeeves.tenant}"
        self.postgres_password = OnePasswordUtil(
            tenant=f"Jeeves_{jeeves.tenant}",
            server_item="application-config",
            vault="Jeeves",
        ).get_key("pg_password")
        self.image_tag = "production" if self.env == "production" else "sprint"

    def payload(self: "AlembicJob") -> dict:
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
                                    )
                                ],
                                command=["/bin/sh", "-c"],
                                args=["python3 /app/provisioning/alembic_migration.py"],
                            )
                        ],
                        volumes=[
                            V1Volume(
                                name="jeeves-tenant-config",
                                config_map=V1ConfigMapVolumeSource(
                                    name="jeeves-tenant-config",
                                    items=[V1KeyToPath(key="tenant-config.json", path="tenant-config.json")],
                                ),
                            )
                        ],
                        restart_policy="Never",
                    )
                )
            ),
        )

        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self: "AlembicJob") -> None:
        """
        Put method
        """
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource, body=self.payload(), field_manager="kubectl-client-side-apply"
        )
        log_info(f"Alembic Job created for {self.jeeves.tenant}")

    def delete(self: "AlembicJob") -> None:
        """
        Delete method
        """
        try:
            self.k8s_dynamic_client.delete(resource=self.resource, name=self.job_name, namespace=self.jeeves.tenant)
        except NotFoundError:
            logger.error(f"Provisioning job not found for {self.jeeves.tenant}")


class VespaJob(K8sResourceBaseClass):
    """
    Vespa Job
    """

    def __init__(self: "VespaJob", jeeves: JeevesSpec) -> None:
        """
        Constructor
        """
        self.jeeves: JeevesSpec = jeeves
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Job, api_version="batch/v1"
        )
        self.env = get_settings().env
        self.job_name = "jeeves-vespa-job"
        self.job_type = "vespa"
        self.image_tag = "production" if self.env == "production" else "sprint"

    def payload(self: "VespaJob") -> dict:
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
                        image_pull_secrets=[V1LocalObjectReference(name="registrycred")],
                        containers=[
                            V1Container(
                                name=self.job_name,
                                env=[
                                    V1EnvVar(name="APP_CONFIG_FILE", value="/config/tenant-config.json"),
                                    V1EnvVar(name="APP_CONFIG_DIR", value="/config"),
                                    V1EnvVar(name="DEPLOYMENT", value=self.env),
                                    V1EnvVar(name="CLIENT_CODE", value=self.jeeves.tenant),
                                ],
                                volume_mounts=[
                                    V1VolumeMount(
                                        name="jeeves-tenant-config",
                                        mount_path="/config/tenant-config.json",
                                        sub_path="tenant-config.json",
                                        read_only=True,
                                    )
                                ],
                                image=f"registry.314ecorp.tech/jeeves-app:{self.image_tag}",
                                command=["/bin/sh", "-c"],
                                args=["python3 /app/provisioning/vespa_setup.py"],
                            )
                        ],
                        volumes=[
                            V1Volume(
                                name="jeeves-tenant-config",
                                config_map=V1ConfigMapVolumeSource(
                                    name="jeeves-tenant-config",
                                    items=[V1KeyToPath(key="tenant-config.json", path="tenant-config.json")],
                                ),
                            ),
                            V1Volume(
                                name="vespa-volume",
                                persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(
                                    claim_name="jeeves-vespa-pvc"
                                ),
                            ),
                        ],
                        restart_policy="Never",
                    )
                )
            ),
        )

        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self: "VespaJob") -> None:
        """
        Put method
        """
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource, body=self.payload(), field_manager="kubectl-client-side-apply"
        )
        log_info(f"Vespa Job created for {self.jeeves.tenant}")

    def delete(self: "VespaJob") -> None:
        """
        Delete method
        """
        try:
            self.k8s_dynamic_client.delete(resource=self.resource, name=self.job_name, namespace=self.jeeves.tenant)
        except NotFoundError:
            logger.error(f"Vespa job not found for {self.jeeves.tenant}")
