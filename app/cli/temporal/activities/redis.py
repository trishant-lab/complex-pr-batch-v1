import base64
import datetime
from datetime import timedelta

from kubernetes.client import (
    V1ConfigMap,
    V1ConfigMapList,
    V1ConfigMapVolumeSource,
    V1Container,
    V1ContainerPort,
    V1EnvVar,
    V1EnvVarSource,
    V1KeyToPath,
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
    V1Volume,
    V1VolumeMount,
)
from temporalio import activity
from temporalio.common import RetryPolicy

from app.cli.k8s_util import (
    ResourceKindEnum,
    api_client,
    get_dynamic_client,
    get_k8s_core_v1_api_client,
    get_resource,
)
from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.temporal.core.base import Activity, LaunchpadCLIBaseModel
from app.cli.temporal.core.log import log_info

CACHE_HOST = "cache.{tenant}.svc.cluster.local"
CACHE_PORT = 6379
CACHE_SERVICE_NAME = "cache"
CACHE_SECRET_NAME = "cache-secret"
CONFIGMAP_NAME = "cache-config"
CONFIGMAP_KEY = "cache.conf"
CONFIG_VOLUME_NAME = "cache-config-volume"
CONFIG_VOLUME_MOUNT_PATH = "/config/cache.conf"


def get_secret(namespace: str, secret_name: str, secret_key: str) -> str:
    """
    Get secret
    """
    k8s_client = get_k8s_core_v1_api_client()
    secret = k8s_client.read_namespaced_secret(
        name=secret_name,
        namespace=namespace,
    )
    return base64.b64decode(secret.data[secret_key]).decode()


async def restart_cache_statefulset(namespace: str) -> None:
    """
    Restart statefulset
    """
    _now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat() + "Z"
    body = {"spec": {"template": {"metadata": {"annotations": {"kubectl.kubernetes.io/restartedAt": _now}}}}}
    api_client.AppsV1Api().patch_namespaced_stateful_set(
        name=CACHE_SERVICE_NAME,
        namespace=namespace,
        body=body,
    )


class CacheConfigMap:
    """
    Cache ConfigMap
    """

    def __init__(self: "CacheConfigMap", tenant: str) -> None:
        """
        Constructor
        """
        self.core_v1_api = get_k8s_core_v1_api_client()
        self.namespace = tenant
        self.name = CONFIGMAP_NAME

    def get_configmap(self: "CacheConfigMap") -> dict | None:
        """
        Get and parse configmap data
        Returns dict of key-value pairs from configmap data or None if not found
        """
        configmaps: V1ConfigMapList = self.core_v1_api.list_namespaced_config_map(
            namespace=self.namespace, field_selector=f"metadata.name={self.name}"
        )

        if not configmaps.items:
            return None

        raw_data = configmaps.items[0].data
        parsed_data = {}
        for value in raw_data.values():
            for line in value.split("\n"):
                if line:  # Skip empty lines
                    key, value = line.split(" ", 1)  # Split on first space only
                    parsed_data[key] = value

        return parsed_data

    def create_or_update_configmap(self: "CacheConfigMap", product: str, redis_tenant_password: str) -> None:
        """
        Create or update configmap
        """
        data = self.get_configmap()

        if data and f"namespace.{product}" not in data:
            data[f"namespace.{product}"] = redis_tenant_password
            self.core_v1_api.replace_namespaced_config_map(
                namespace=self.namespace,
                name=self.name,
                body=V1ConfigMap(
                    api_version="v1",
                    kind=ResourceKindEnum.ConfigMap.value,
                    metadata=V1ObjectMeta(namespace=self.namespace, name=self.name),
                    data={"cache.conf": "\n".join(f"{k} {v}" for k, v in data.items())},
                ),
            )
        elif not data:
            data = {"port": CACHE_PORT, f"namespace.{product}": redis_tenant_password}
            self.core_v1_api.create_namespaced_config_map(
                namespace=self.namespace,
                body=V1ConfigMap(
                    api_version="v1",
                    kind=ResourceKindEnum.ConfigMap.value,
                    metadata=V1ObjectMeta(namespace=self.namespace, name=self.name),
                    data={"cache.conf": "\n".join(f"{k} {v}" for k, v in data.items())},
                ),
            )
        log_info(f"ConfigMap {self.name} created successfully")

    def delete_namespace_from_configmap(self: "CacheConfigMap", product: str) -> None:
        """
        Delete configmap
        """
        data = self.get_configmap()
        if data and f"namespace.{product}" in data:
            data.pop(f"namespace.{product}")
            self.core_v1_api.replace_namespaced_config_map(
                namespace=self.namespace,
                name=self.name,
                body=V1ConfigMap(
                    api_version="v1",
                    kind=ResourceKindEnum.ConfigMap.value,
                    metadata=V1ObjectMeta(namespace=self.namespace, name=self.name),
                    data={CONFIGMAP_KEY: "\n".join(f"{k} {v}" for k, v in data.items())},
                ),
            )
        log_info(f"Namespace {product} deleted successfully from configmap {self.name}")


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

        CacheConfigMap(activity_model.namespace).create_or_update_configmap(
            product=activity_model.product,
            redis_tenant_password=activity_model.redis_tenant_password,
        )

        body = V1StatefulSet(
            api_version="apps/v1",
            kind=ResourceKindEnum.StatefulSet.value,
            metadata=V1ObjectMeta(namespace=activity_model.namespace, name=CACHE_SERVICE_NAME),
            spec=V1StatefulSetSpec(
                replicas=1,
                selector={"matchLabels": {"app": CACHE_SERVICE_NAME, "kind": "redis"}},
                service_name=f"{CACHE_SERVICE_NAME}-service",
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(labels={"app": CACHE_SERVICE_NAME, "kind": "redis"}),
                    spec=V1PodSpec(
                        image_pull_secrets=[V1LocalObjectReference(name="registrycred")],
                        node_selector={"app": "314e"},
                        containers=[
                            V1Container(
                                name=CACHE_SERVICE_NAME,
                                image="apache/kvrocks:2.5.1",
                                args=["--requirepass", "$(REDIS_PASSWORD)", "--config", CONFIG_VOLUME_MOUNT_PATH],
                                ports=[V1ContainerPort(container_port=CACHE_PORT, protocol="TCP")],
                                image_pull_policy="Always",
                                env=[
                                    V1EnvVar(
                                        name="REDIS_PASSWORD",
                                        value_from=V1EnvVarSource(
                                            secret_key_ref=V1SecretKeySelector(
                                                key="REDIS_PASSWORD", name=CACHE_SECRET_NAME
                                            )
                                        ),
                                    )
                                ],
                                volume_mounts=[
                                    V1VolumeMount(
                                        name=CONFIG_VOLUME_NAME,
                                        mount_path=CONFIG_VOLUME_MOUNT_PATH,
                                        sub_path=CONFIGMAP_KEY,
                                    )
                                ],
                            )
                        ],
                        volumes=[
                            V1Volume(
                                name=CONFIG_VOLUME_NAME,
                                config_map=V1ConfigMapVolumeSource(
                                    name=CONFIGMAP_NAME,
                                    items=[V1KeyToPath(key=CONFIGMAP_KEY, path=CONFIGMAP_KEY)],
                                ),
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
        log_info(f"Redis {CACHE_SERVICE_NAME} created successfully")


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

        CacheConfigMap(activity_model.namespace).create_or_update_configmap(
            product=activity_model.product,
            redis_tenant_password=get_secret(
                namespace=activity_model.namespace,
                secret_name=activity_model.secret_name,
                secret_key=activity_model.password_key,
            ),
        )

        body = V1StatefulSet(
            api_version="apps/v1",
            kind=ResourceKindEnum.StatefulSet.value,
            metadata=V1ObjectMeta(namespace=activity_model.namespace, name=CACHE_SERVICE_NAME),
            spec=V1StatefulSetSpec(
                replicas=1,
                selector={"matchLabels": {"app": CACHE_SERVICE_NAME, "kind": "redis"}},
                service_name=f"{CACHE_SERVICE_NAME}-service",
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(labels={"app": CACHE_SERVICE_NAME, "kind": "redis"}),
                    spec=V1PodSpec(
                        image_pull_secrets=[V1LocalObjectReference(name="registrycred")],
                        node_selector={"app": "314e"},
                        containers=[
                            V1Container(
                                name=CACHE_SERVICE_NAME,
                                image="apache/kvrocks:2.5.1",
                                args=["--requirepass", "$(REDIS_PASSWORD)", "--config", CONFIG_VOLUME_MOUNT_PATH],
                                ports=[V1ContainerPort(container_port=CACHE_PORT, protocol="TCP")],
                                image_pull_policy="Always",
                                env=[
                                    V1EnvVar(
                                        name="REDIS_PASSWORD",
                                        value_from=V1EnvVarSource(
                                            secret_key_ref=V1SecretKeySelector(
                                                key="REDIS_PASSWORD", name=CACHE_SECRET_NAME
                                            )
                                        ),
                                    )
                                ],
                                volume_mounts=[
                                    V1VolumeMount(
                                        name=CONFIG_VOLUME_NAME,
                                        mount_path=CONFIG_VOLUME_MOUNT_PATH,
                                        sub_path=CONFIGMAP_KEY,
                                    )
                                ],
                            )
                        ],
                        volumes=[
                            V1Volume(
                                name=CONFIG_VOLUME_NAME,
                                config_map=V1ConfigMapVolumeSource(
                                    name=CONFIGMAP_NAME,
                                    items=[V1KeyToPath(key=CONFIGMAP_KEY, path=CONFIGMAP_KEY)],
                                ),
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
        log_info(f"Redis {CACHE_SERVICE_NAME} created successfully")


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

        CacheConfigMap(activity_model.namespace).delete_namespace_from_configmap(activity_model.product)
        await restart_cache_statefulset(activity_model.namespace)
