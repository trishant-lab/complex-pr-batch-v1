from kubernetes.client import V1Job, V1JobSpec, V1JobTemplateSpec, V1PodSpec, \
    V1LocalObjectReference, V1Container, V1EnvVar, V1VolumeMount, V1Volume, V1ConfigMapVolumeSource, V1KeyToPath, \
    V1PersistentVolumeClaimVolumeSource, V1SecretKeySelector, V1EnvVarSource
from kubernetes.client import V1ObjectMeta
from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.dexit.dexit import DexitSpec
from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.core.settings import get_settings


class AtlasJob(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self, dexit: DexitSpec) -> None:
        self.dexit: DexitSpec = dexit
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Job, api_version="v1"
        )
        self.env = get_settings().env
        self.job_name = "dexit-atlas-migration-job"
        self.job_type = "atlas"
        self.postgres_user = f"dexit_{dexit.tenant}"
        self.image_tag = "production" if self.env == "production" else "sprint"

    def payload(self):
        body = V1Job(
            api_version="batch/v1",
            kind=ResourceKindEnum.Job.value,
            metadata=V1ObjectMeta(
                namespace=self.dexit.tenant,
                name=self.job_name,
                labels={"app": "dexit", "jobKind": self.job_type},
                annotations={"app": "dexit", "jobKind": self.job_type}
            ),
            spec=V1JobSpec(
                template=V1JobTemplateSpec(
                    spec=V1PodSpec(
                        image_pull_secrets=[V1LocalObjectReference(name="registrycred")],
                        containers=[
                            V1Container(
                                name=self.job_name,
                                image=f"registry.314ecorp.tech/dexit-app:{self.image_tag}",
                                env=[
                                    V1EnvVar(name="POSTGRES_PASSWORD", value_from=V1EnvVarSource(
                                            secret_key_ref=V1SecretKeySelector(
                                                key="POSTGRES_PASSWORD",
                                                name="dexit-postgres-password"
                                            )
                                        )
                                    ),
                                    V1EnvVar(name="POSTGRES_USER", value=self.postgres_user),
                                    V1EnvVar(name="APP_CONFIG_DIR", value="/config"),
                                    V1EnvVar(name="DEPLOYMENT", value=self.env),
                                    V1EnvVar(name="CLIENT_CODE", value=self.dexit.tenant)
                                ],
                                volume_mounts=[
                                    V1VolumeMount(
                                        name="dexit-env-config",
                                        mount_path="/config/env-config.json",
                                        sub_path="env-config.json",
                                        read_only=True
                                    ),
                                    V1VolumeMount(
                                        name="dexit-tenant-config",
                                        mount_path="/config/tenant-config.json",
                                        sub_path="tenant-config.json",
                                        read_only=True
                                    )
                                ],
                                command=["/bin/sh", "-c"],
                                args=[
                                    "python3 /app/provisioning/atlas_migration.py"
                                ]
                            )
                        ],
                        volumes=[
                            V1Volume(
                                name="dexit-env-config",
                                config_map=V1ConfigMapVolumeSource(
                                    name="dexit-env-config",
                                    items=[V1KeyToPath(key="env-config.json", path="env-config.json")]
                                )
                            ),
                            V1Volume(
                                name="dexit-tenant-config",
                                config_map=V1ConfigMapVolumeSource(
                                    name="dexit-tenant-config",
                                    items=[V1KeyToPath(
                                        key="tenant-config.json", path="tenant-config.json"
                                    )]
                                )
                            ),
                        ],
                        restart_policy="Never"
                    )
                )
            )
        )

        job_body = self.k8s_dynamic_client.client.sanitize_for_serialization(body)
        return job_body

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
                name=self.job_name,
                namespace=self.dexit.tenant
            )
        except NotFoundError:
            logger.error(f"Provisioning job not found for {self.dexit.tenant}")


class VespaJob(K8sResourceBaseClass):
    """
    Vespa Job
    """
    def __init__(self, dexit: DexitSpec) -> None:
        self.dexit: DexitSpec = dexit
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Job, api_version="batch/v1"
        )
        self.env = get_settings().env
        self.job_name = "dexit-vespa-job"
        self.job_type = "vespa"
        self.image_tag = "production" if self.env == "production" else "sprint"

    def payload(self):
        """
        Job Payload
        """
        body = V1Job(
            api_version="batch/v1",
            kind=ResourceKindEnum.Job.value,
            metadata=V1ObjectMeta(
                namespace=self.dexit.tenant,
                name=self.job_name,
                labels={"app": "dexit", "jobKind": self.job_type},
                annotations={"app": "dexit", "jobKind": self.job_type}
            ),
            spec=V1JobSpec(
                template=V1JobTemplateSpec(
                    spec=V1PodSpec(
                        image_pull_secrets=[V1LocalObjectReference(name="registrycred")],
                        containers=[
                            V1Container(
                                name=self.job_name,
                                env=[
                                    V1EnvVar(name="APP_CONFIG_DIR", value="/config"),
                                    V1EnvVar(name="DEPLOYMENT", value=self.env),
                                    V1EnvVar(name="CLIENT_CODE", value=self.dexit.tenant)
                                ],
                                volume_mounts=[
                                    V1VolumeMount(
                                        name="dexit-env-config",
                                        mount_path="/config/env-config.json",
                                        sub_path="env-config.json",
                                        read_only=True
                                    ),
                                    V1VolumeMount(
                                        name="dexit-tenant-config",
                                        mount_path="/config/tenant-config.json",
                                        sub_path="tenant-config.json",
                                        read_only=True
                                    )
                                ],
                                image=f"registry.314ecorp.tech/dexit-app:{self.image_tag}",
                                command=["/bin/sh", "-c"],
                                args=[
                                    f"dexit --tenant-name {self.dexit.tenant} customer --create"
                                ]
                            )
                        ],
                        volumes=[
                            V1Volume(
                                name="dexit-env-config",
                                config_map=V1ConfigMapVolumeSource(
                                    name="dexit-env-config",
                                    items=[V1KeyToPath(key="env-config.json", path="env-config.json")]
                                )
                            ),
                            V1Volume(
                                name="dexit-tenant-config",
                                config_map=V1ConfigMapVolumeSource(
                                    name="dexit-tenant-config",
                                    items=[V1KeyToPath(
                                        key="tenant-config.json", path="tenant-config.json"
                                    )]
                                )
                            ),
                            V1Volume(
                                name="vespa-volume",
                                persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(
                                    claim_name="dexit-vespa-pvc"
                                )
                            )
                        ],
                        restart_policy="Never"
                    )
                )
            )
        )

        job_body = self.k8s_dynamic_client.client.sanitize_for_serialization(body)

        return job_body

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
                name=self.job_name,
                namespace=self.dexit.tenant
            )
        except NotFoundError:
            logger.error(f"Vespa job not found for {self.dexit.tenant}")
