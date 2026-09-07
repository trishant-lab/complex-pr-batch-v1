import asyncio
from datetime import timedelta

from kubernetes.client import (
    BatchV1Api,
    V1Container,
    V1DeleteOptions,
    V1EnvVar,
    V1Job,
    V1JobSpec,
    V1JobTemplateSpec,
    V1ObjectMeta,
    V1PodSpec,
)
from kubernetes.dynamic.exceptions import NotFoundError
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.k8s_util import ResourceKindEnum, get_dynamic_client, get_resource
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_error, log_info

JOB_NAME = "rocketmq-topic-setup"
JOB_API_VERSION = "batch/v1"

# Consumer groups are not created here; the engine names one per route at runtime and the
# broker creates them on demand.
TOPIC_SUFFIXES = ("inbound", "outbound", "message-trace", "event", "event-response", "alert")

POLL_INTERVAL_SECONDS = 5
POLL_ATTEMPTS = 60


class RocketMQProperties(LaunchpadCLIBaseModel):
    """
    RocketMQProperties
    """

    tenant: str
    namespace: str
    name_server: str
    cluster_name: str = "DefaultCluster"
    docker_image: str = "apache/rocketmq:5.3.2"
    queue_nums: int = 8


def topic_names(tenant: str) -> list[str]:
    """
    Topic names zsegment-api and zsegment-engine expect for a tenant
    """
    return [f"zsegment-{tenant}-{suffix}" for suffix in TOPIC_SUFFIXES]


def build_mqadmin_script(properties: RocketMQProperties) -> str:
    """
    Build the shell script that creates the tenant topics
    """
    topics = " ".join(topic_names(properties.tenant))
    return (
        "set -eu\n"
        "MQADMIN=$(ls /home/rocketmq/rocketmq-*/bin/mqadmin | head -1)\n"
        f"for TOPIC in {topics}; do\n"
        '  echo "creating $TOPIC"\n'
        f'  sh "$MQADMIN" updateTopic -n {properties.name_server} -c {properties.cluster_name} '
        f'-t "$TOPIC" -r {properties.queue_nums} -w {properties.queue_nums}\n'
        "done\n"
    )


def delete_job(namespace: str) -> None:
    """
    Delete a previous run of the job
    """
    k8s_dynamic_client = get_dynamic_client()
    resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Job, api_version=JOB_API_VERSION)

    try:
        resource.get(name=JOB_NAME, namespace=namespace)
    except NotFoundError:
        return

    try:
        BatchV1Api().delete_namespaced_job(
            name=JOB_NAME, namespace=namespace, body=V1DeleteOptions(propagation_policy="Foreground")
        )
        log_info(f"Deleted existing job {JOB_NAME} in namespace {namespace}")
    except Exception as e:
        log_error(f"Error during deletion of job {JOB_NAME} in namespace {namespace}: {e}")


def create_job(properties: RocketMQProperties) -> None:
    """
    Create the mqadmin job in the tenant namespace
    """
    k8s_dynamic_client = get_dynamic_client()
    resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Job, api_version=JOB_API_VERSION)

    body = V1Job(
        api_version=JOB_API_VERSION,
        kind=ResourceKindEnum.Job.value,
        metadata=V1ObjectMeta(
            namespace=properties.namespace,
            name=JOB_NAME,
            labels={"app": "zsegment", "jobKind": "rocketmq-topic-setup"},
        ),
        spec=V1JobSpec(
            backoff_limit=3,
            ttl_seconds_after_finished=600,
            template=V1JobTemplateSpec(
                spec=V1PodSpec(
                    node_selector={"app": "314e"},
                    restart_policy="Never",
                    containers=[
                        V1Container(
                            name=JOB_NAME,
                            image=properties.docker_image,
                            env=[V1EnvVar(name="NAMESRV_ADDR", value=properties.name_server)],
                            command=["/bin/sh", "-c"],
                            args=[build_mqadmin_script(properties)],
                        )
                    ],
                )
            ),
        ),
    )

    payload = k8s_dynamic_client.client.sanitize_for_serialization(body)
    k8s_dynamic_client.server_side_apply(
        resource=resource, body=payload, field_manager="kubectl-client-side-apply", force_conflicts=True
    )
    log_info(f"Job {JOB_NAME} created in namespace {properties.namespace}")


async def wait_for_job(namespace: str) -> None:
    """
    Wait for the job to succeed
    """
    batch_v1 = BatchV1Api()

    for _ in range(POLL_ATTEMPTS):
        status = batch_v1.read_namespaced_job_status(name=JOB_NAME, namespace=namespace).status
        if status.succeeded:
            log_info(f"Job {JOB_NAME} completed in namespace {namespace}")
            return
        if status.failed:
            raise RuntimeError(f"Job {JOB_NAME} failed in namespace {namespace}")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

    raise RuntimeError(
        f"Job {JOB_NAME} did not complete within "
        f"{POLL_ATTEMPTS * POLL_INTERVAL_SECONDS} seconds in namespace {namespace}"
    )


class RocketMQTopicSetupActivity(Activity):
    """
    RocketMQTopicSetupActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Timeout for the activity
        """
        return timedelta(minutes=10)

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
    @activity.defn(name="RocketMQTopicSetupActivity")
    async def defn(properties: RocketMQProperties) -> None:
        """
        Create the RocketMQ topics for the tenant by running mqadmin as a job
        """
        log_info(f"Starting RocketMQ topic setup for tenant {properties.tenant}")

        delete_job(properties.namespace)
        create_job(properties)
        await wait_for_job(properties.namespace)

        log_info(f"RocketMQ topic setup completed for tenant {properties.tenant}")
