from pathlib import Path
import shutil
import tempfile
import aiohttp
from lxml import etree

from temporalio import activity
from temporalio.common import RetryPolicy


from datetime import datetime, timedelta
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

from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.jeeves.models.jeevesSpec import JeevesSpec
from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.temporal.core.log import log_info, log_error
from app.core.settings import get_settings


TENANT_CONFIG_FILE = "tenant-config.json"


class VespaDeleteActivityModel(LaunchpadCLIBaseModel):
    schema_name: str


class VespaDeleteActivity(Activity):
    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(seconds=240)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        RetryPolicy for the activity
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=3,
        )

    @staticmethod
    @activity.defn(name="VespaDeleteActivity")
    async def defn(activity_input: VespaDeleteActivityModel) -> None:
        """
        Callable for the activity
        """
        config = get_settings()
        user_schema_name: str = f"{activity_input.schema_name}{config.jeeves.vespa_user_index_suffix}"
        tree = etree.parse(f"{config.jeeves.vespa_application_path}/services.xml")  # nosec
        root = tree.getroot()
        docs = root.find("content").find("documents")
        [
            docs.remove(doc)
            for doc in docs.findall("document")
            if doc.get("type") == activity_input.schema_name or doc.get("type") == user_schema_name
        ]
        tree = etree.ElementTree(root)
        etree.indent(tree, " ")
        tree.write(f"{config.jeeves.vespa_application_path}/services.xml")

        validation_tree = etree.parse(f"{config.jeeves.vespa_application_path}/validation-overrides.xml")  # nosec
        validation_root = validation_tree.getroot()
        docs = validation_root.findall("allow")
        [docs.remove(doc) for doc in docs if doc.text == "schema-removal"]
        new_allow_element = etree.Element("allow")
        new_allow_element.text = "schema-removal"
        new_allow_element.set("until", (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d"))
        validation_root.append(new_allow_element)
        validation_tree = etree.ElementTree(validation_root)
        etree.indent(validation_tree, " ")
        validation_tree.write(f"{config.jeeves.vespa_application_path}/validation-overrides.xml")

        try:
            Path(f"{config.jeeves.vespa_application_path}/schemas/" + activity_input.schema_name + ".sd").unlink()
            Path(f"{config.jeeves.vespa_application_path}/schemas/" + user_schema_name + ".sd").unlink()
            zip_path: Path = Path(config.jeeves.vespa_application_path, "application.zip")
            if zip_path.exists():
                zip_path.unlink()
                with tempfile.TemporaryDirectory() as temp_directory:
                    temp_application_path: Path = Path(temp_directory, "application")
                    shutil.copytree(config.jeeves.vespa_application_path, temp_application_path)
                    shutil.make_archive(
                        str(zip_path.with_suffix("")),
                        "zip",
                        temp_application_path,
                    )
                deploy_url: str = (
                    f"{config.jeeves.vespa_host}:{config.jeeves.vespa_deploy_port_address}"
                    f"/application/v2/tenant/default/prepareandactivate"
                )
                async with aiohttp.ClientSession() as session:
                    with open(zip_path, "rb") as zip_file:
                        file_content = zip_file.read()
                        response = await session.post(
                            deploy_url,
                            headers={"Content-Type": "application/zip"},
                            data=file_content,
                            timeout=aiohttp.ClientTimeout(total=120),
                        )
                        if response.status != 200:
                            log_error("Could not delete index")
        except Exception:
            log_error("Could not delete index")


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
                                    V1EnvVar(name="APP_CONFIG_FILE", value=f"/config/{TENANT_CONFIG_FILE}"),
                                    V1EnvVar(name="APP_CONFIG_DIR", value="/config"),
                                    V1EnvVar(name="DEPLOYMENT", value=self.env),
                                    V1EnvVar(name="CLIENT_CODE", value=self.jeeves.tenant),
                                ],
                                volume_mounts=[
                                    V1VolumeMount(
                                        name="jeeves-tenant-config",
                                        mount_path=f"/config/{TENANT_CONFIG_FILE}",
                                        sub_path=TENANT_CONFIG_FILE,
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
                                    items=[V1KeyToPath(key=TENANT_CONFIG_FILE, path=TENANT_CONFIG_FILE)],
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
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
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
