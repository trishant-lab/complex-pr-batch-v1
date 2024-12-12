from temporalio import activity, workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    import asyncio
    import base64
    from datetime import timedelta

    from kubernetes.client import (
        V1Container,
        V1ContainerPort,
        V1EnvVar,
        V1EnvVarSource,
        V1LocalObjectReference,
        V1ObjectMeta,
        V1PodSpec,
        V1PodTemplateSpec,
        V1SecretKeySelector,
        V1Service,
        V1ServicePort,
        V1ServiceSpec,
        V1StatefulSet,
        V1StatefulSetSpec,
    )
    from redis import Redis

    from app.cli.k8s_util import (
        DynamicClient,
        ResourceKindEnum,
        get_dynamic_client,
        get_k8s_core_v1_api_client,
        get_resource,
    )
    from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
    from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
    from app.cli.temporal.core.log import log_info

CACHE_HOST = "cache-new.{tenant}.svc.cluster.local"


class RedisService(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self: "RedisService", tenant: str) -> None:
        """
        Constructor
        """
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Service, api_version="v1"
        )
        self.tenant = tenant

    def payload(self: "RedisService") -> None:
        """
        k8s resource payload
        """
        body = V1Service(
            api_version="v1",
            kind=ResourceKindEnum.Service.value,
            metadata=V1ObjectMeta(
                name="cache-new",
                namespace=self.tenant,
                labels={"app": "cache", "kind": "redis"},
            ),
            spec=V1ServiceSpec(
                selector={"app": "cache", "kind": "redis"},
                type="ClusterIP",
                ports=[
                    V1ServicePort(
                        name="redis",
                        port=6379,
                        target_port=6379,
                    )
                ],
            ),
        )

        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self: "RedisService") -> None:
        """
        k8s server side apply
        """
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource, body=self.payload(), field_manager="kubectl-client-side-apply"
        )
        log_info("Service cache-new-service created successfully")

    def delete(self: "RedisService") -> None:
        """
        Don't delete Service
        """
        # Don't delete Service
        pass


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
        name = "cache"

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
        RedisService(activity_model.namespace).put()
        log_info(f"Redis {name} created successfully")

        await asyncio.sleep(30)

        create_product_namespace(
            tenant=activity_model.namespace,
            product=activity_model.product,
            redis_tenant_password=activity_model.redis_tenant_password,
            k8s_dynamic_client=k8s_dynamic_client,
        )

        log_info(f"Product namespace {activity_model.namespace} created successfully")


class RedisSetupFromSecretActivityModel(LaunchpadCLIBaseModel):
    """
    RedisSetupFromSecretActivityModel
    """

    namespace: str
    product: str
    secret_name: str
    password_key: str = "password"


class RedisSetupFromSecretActivity(Activity):
    """
    RedisSetupFromSecretActivity
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
    @activity.defn(name="RedisSetupFromSecretActivity")
    async def defn(activity_model: RedisSetupFromSecretActivityModel) -> None:
        """
        Create redis setup
        """
        k8s_dynamic_client = get_dynamic_client()
        redis_resource = get_resource(
            dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.StatefulSet, api_version="apps/v1"
        )
        name = "cache"

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
            resource=redis_resource,
            body=payload,
            field_manager="kubectl-client-side-apply",
        )
        RedisService(activity_model.namespace).put()
        log_info(f"Redis {name} created successfully")

        # wait for redis to be ready
        await asyncio.sleep(30)

        _create_redis_namespace_for_product(
            activity_model=activity_model,
            k8s_dynamic_client=k8s_dynamic_client,
            tenant=activity_model.namespace,
            product=activity_model.product,
        )

        log_info(f"Product namespace {activity_model.namespace} created successfully")


def _create_redis_namespace_for_product(
    activity_model: RedisSetupFromSecretActivityModel,
    k8s_dynamic_client: DynamicClient,
    tenant: str,
    product: str,
) -> None:
    """
    Create redis namespace for product. Read secret from k8s and create namespace in redis
    """
    k8s_client = get_k8s_core_v1_api_client()
    secret = k8s_client.read_namespaced_secret(
        name=activity_model.secret_name,
        namespace=activity_model.namespace,
    )
    redis_tenant_password = base64.b64decode(secret.data[activity_model.password_key]).decode()
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


def delete_product_namespace(tenant: str, product: str, k8s_dynamic_client: DynamicClient) -> None:
    """
    Delete namespace in redis
    """
    redis_host = CACHE_HOST.format(tenant=tenant)
    redis_port = 6379

    resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Secret, api_version="v1")

    secret = base64.b64decode(
        k8s_dynamic_client.get(resource, namespace=tenant, name="cache-secret").data.get("REDIS_PASSWORD")
    )

    redis = Redis(host=redis_host, port=redis_port, password=secret)

    response = redis.execute_command("namespace", "GET", product)

    if response:
        redis.execute_command("namespace", "DEL", product)
    else:
        log_info(f"Namespace {product} not found in redis")


class RedisDeleteNamespaceActivityModel(LaunchpadCLIBaseModel):
    """
    RedisDeleteNamespaceActivityModel
    """

    namespace: str
    product: str


class RedisDeleteNamespaceActivity(Activity):
    """
    RedisDeleteNamespaceActivity
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """
        Get timeout
        """
        return timedelta(seconds=120)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """
        Get retry policy
        """
        return RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)

    @staticmethod
    @activity.defn(name="RedisDeleteNamespaceActivity")
    async def defn(activity_model: RedisDeleteNamespaceActivityModel) -> None:
        """
        Delete redis namespace
        """
        k8s_dynamic_client = get_dynamic_client()

        delete_product_namespace(
            tenant=activity_model.namespace,
            product=activity_model.product,
            k8s_dynamic_client=k8s_dynamic_client,
        )
