import asyncio
import base64
from datetime import timedelta
from redis import Redis
from temporalio import activity
from temporalio.common import RetryPolicy
from kubernetes.client import (
    V1StatefulSet,
    V1ObjectMeta,
    V1StatefulSetSpec,
    V1PodTemplateSpec,
    V1PodSpec,
    V1LocalObjectReference,
    V1Container,
    V1ContainerPort,
    V1EnvVar,
    V1EnvVarSource,
    V1SecretKeySelector,
)

from app.cli.k8s_util import ResourceKindEnum, get_dynamic_client, get_resource, DynamicClient
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info

CACHE_HOST = "cache-new.{tenant}.svc.cluster.local"


def create_product_namespace(
    tenant: str, product: str, redis_tenant_password: str, k8s_dynamic_client: DynamicClient
) -> None:
    """
    Create namespace in redis
    """
    redis_host = CACHE_HOST.format(tenant=tenant)
    redis_port = 6379

    resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Secret, api_version="v1")

    secret = base64.b64decode(
        k8s_dynamic_client.get(resource, namespace=tenant, name="cache-secret").data.get("REDIS_PASSWORD")
    ).decode()

    redis = Redis(host=redis_host, port=redis_port, password=secret)

    response = redis.execute_command("namespace", "GET", product)

    if response:
        redis.execute_command("namespace", "SET", product, redis_tenant_password)
    else:
        redis.execute_command("namespace", "ADD", product, redis_tenant_password)


class RedisSetupActivityModel(LaunchpadCLIBaseModel):
    """
    RedisSetupActivityModel
    """

    namespace: str
    product: str
    redis_tenant_password: str


class RedisSetupActivity(Activity):
    """
    RedisSetupActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=300)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

    @staticmethod
    @activity.defn(name="RedisSetupActivity")
    async def defn(activity_model: RedisSetupActivityModel) -> None:
        """
        Create redis setup
        """
        k8s_dynamic_client = get_dynamic_client()
        redis_resource = get_resource(
            dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.StatefulSet, api_version="apps/v1"
        )
        name = "cache-new"

        body = V1StatefulSet(
            api_version="apps/v1",
            kind=ResourceKindEnum.StatefulSet.value,
            metadata=V1ObjectMeta(namespace=activity_model.namespace, name=name),
            spec=V1StatefulSetSpec(
                replicas=1,
                selector={"matchLabels": {"app": name, "kind": "redis"}},
                service_name=f"{name}-service",
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(labels={"app": name, "kind": "redis"}),
                    spec=V1PodSpec(
                        image_pull_secrets=[V1LocalObjectReference(name="registrycred")],
                        node_selector={"app": "314e"},
                        containers=[
                            V1Container(
                                name=name,
                                image="apache/kvrocks:2.5.1",
                                args=["--requirepass", "$(REDIS_PASSWORD)", "--port", "6379"],
                                ports=[V1ContainerPort(container_port=6379, protocol="TCP")],
                                image_pull_policy="Always",
                                env=[
                                    V1EnvVar(
                                        name="REDIS_PASSWORD",
                                        value_from=V1EnvVarSource(
                                            secret_key_ref=V1SecretKeySelector(
                                                key="REDIS_PASSWORD", name="cache-secret"
                                            )
                                        ),
                                    )
                                ],
                            )
                        ],
                    ),
                ),
            ),
        )

        payload = k8s_dynamic_client.client.sanitize_for_serialization(body)
        k8s_dynamic_client.server_side_apply(
            resource=redis_resource, body=payload, field_manager="kubectl-client-side-apply"
        )

        log_info(f"Redis {name} created successfully")

        await asyncio.sleep(30)

        create_product_namespace(
            tenant=activity_model.namespace,
            product=activity_model.product,
            redis_tenant_password=activity_model.redis_tenant_password,
            k8s_dynamic_client=k8s_dynamic_client,
        )

        log_info(f"Product namespace {activity_model.name} created successfully")
