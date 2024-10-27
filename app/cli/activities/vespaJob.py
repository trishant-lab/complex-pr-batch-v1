from temporalio import activity, workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from datetime import timedelta
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
    from kubernetes.dynamic.exceptions import NotFoundError

    from app.cli.temporal.core.base import Activity
    from app.cli.temporal.jeeves.models.jeevesSpec import JeevesSpec
    from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
    from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
    from app.cli.temporal.core.log import log_info, log_error
    from app.core.settings import get_settings


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
                        node_selector={"app": "314e"},
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
                            # V1Volume(
                            #     name="vespa-volume",
                            #     persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(
                            #         claim_name="jeeves-vespa-pvc"
                            #     ),
                            # ),
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
            log_error(f"Vespa job not found for {self.jeeves.tenant}")


class VespaJobActivity(Activity):
    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="VespaJobActivity")
    async def defn(jeeves: JeevesSpec) -> None:
        """
        Callable for the activity
        """
        vespa_job = VespaJob(jeeves=jeeves)
        vespa_job.delete()
        vespa_job.put()
