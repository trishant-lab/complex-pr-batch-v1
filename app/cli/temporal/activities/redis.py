import base64
from datetime import timedelta

import redis as redis_client
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.k8s_util import get_k8s_core_v1_api_client
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info

CACHE_HOST = "cache.cache.svc.cluster.local"
CACHE_PORT = 6379
CACHE_NAMESPACE = "cache"
CACHE_SECRET_NAME = "cache-secret"


def get_kvrocks_namespace_name(product: str, tenant: str) -> str:
    """
    Build a unique KVRocks namespace name from product and tenant to avoid collisions.
    """
    return f"{product}_{tenant}"


def get_cache_master_password() -> str:
    """
    Read the master password from cache-secret in the cache namespace.
    """
    k8s_client = get_k8s_core_v1_api_client()
    secret = k8s_client.read_namespaced_secret(
        name=CACHE_SECRET_NAME,
        namespace=CACHE_NAMESPACE,
    )
    return base64.b64decode(secret.data["REDIS_PASSWORD"]).decode()


def get_redis_connection() -> redis_client.Redis:
    """
    Get a Redis connection to the shared KVRocks instance in the cache namespace.
    """
    return redis_client.Redis(
        host=CACHE_HOST,
        port=CACHE_PORT,
        password=get_cache_master_password(),
        decode_responses=True,
    )


def add_redis_namespace(namespace: str, product: str, token: str) -> None:
    """
    Add a KVRocks namespace using the NAMESPACE ADD command.
    If the namespace already exists, overwrites the token via NAMESPACE SET.
    Pipelines CONFIG REWRITE to persist the change to kvrocks.conf on disk.
    """
    ns_name = get_kvrocks_namespace_name(product, namespace)
    with get_redis_connection() as r:
        try:
            pipe = r.pipeline()
            pipe.execute_command("NAMESPACE", "ADD", ns_name, token)
            pipe.execute_command("CONFIG", "REWRITE")
            pipe.execute()
            log_info(f"Namespace {ns_name} added and persisted to disk")
        except redis_client.ResponseError as e:
            if "namespace" in str(e) and "already exists" in str(e):
                pipe = r.pipeline()
                pipe.execute_command("NAMESPACE", "SET", ns_name, token)
                pipe.execute_command("CONFIG", "REWRITE")
                pipe.execute()
                log_info(f"Namespace {ns_name} already existed, token updated and persisted to disk")
            else:
                raise


def delete_redis_namespace(namespace: str, product: str) -> None:
    """
    Delete a KVRocks namespace using the NAMESPACE DEL command.
    Pipelines CONFIG REWRITE to persist the change to kvrocks.conf on disk.
    """
    ns_name = get_kvrocks_namespace_name(product, namespace)
    with get_redis_connection() as r:
        try:
            pipe = r.pipeline()
            pipe.execute_command("NAMESPACE", "DEL", ns_name)
            pipe.execute_command("CONFIG", "REWRITE")
            pipe.execute()
            log_info(f"Namespace {ns_name} deleted and persisted to disk")
        except redis_client.ResponseError as e:
            if "namespace" in str(e) and "not found" in str(e):
                log_info(f"Namespace {ns_name} not found, nothing to delete")
            else:
                raise


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
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="RedisSetupActivity")
    async def defn(activity_model: RedisSetupActivityModel) -> None:
        """
        Add a namespace to the shared KVRocks instance via NAMESPACE command.
        """
        add_redis_namespace(
            namespace=activity_model.namespace,
            product=activity_model.product,
            token=activity_model.redis_tenant_password,
        )


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
    RedisSetupFromSecretActivity — reads the namespace token from a tenant K8s secret.
    """

    @staticmethod
    def get_timeout() -> timedelta:
        """Get timeout."""
        return timedelta(seconds=300)

    @staticmethod
    def get_retry_policy() -> RetryPolicy:
        """Get retry policy."""
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="RedisSetupFromSecretActivity")
    async def defn(activity_model: RedisSetupFromSecretActivityModel) -> None:
        """
        Read namespace token from tenant secret and add namespace to the shared KVRocks instance.
        """
        k8s_client = get_k8s_core_v1_api_client()
        secret = k8s_client.read_namespaced_secret(
            name=activity_model.secret_name,
            namespace=activity_model.namespace,
        )
        token = base64.b64decode(secret.data[activity_model.password_key]).decode()
        add_redis_namespace(
            namespace=activity_model.namespace,
            product=activity_model.product,
            token=token,
        )


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
        return RetryPolicy(
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=3,
            maximum_attempts=5,
        )

    @staticmethod
    @activity.defn(name="RedisDeleteNamespaceActivity")
    async def defn(activity_model: RedisDeleteNamespaceActivityModel) -> None:
        """
        Delete a namespace from the shared KVRocks instance via NAMESPACE command.
        """
        delete_redis_namespace(namespace=activity_model.namespace, product=activity_model.product)
