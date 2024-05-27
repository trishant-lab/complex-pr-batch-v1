import base64

from kubernetes.client import (
    V1StatefulSet, V1ObjectMeta, V1StatefulSetSpec, V1PodTemplateSpec, V1PodSpec, V1LocalObjectReference, V1Container,
    V1ContainerPort, V1EnvVar, V1EnvVarSource, V1SecretKeySelector, V1Service, V1ServiceSpec, V1ServicePort
)
from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger
from redis import Redis

from app.cli.jeeves.common import JeevesSpec, ProductName
from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.common import generate_password
from app.onepasswordutil import OnePasswordUtil

CACHE_HOST = "cache-new.{tenant}.svc.cluster.local"


def create_product_namespace(jeeves: JeevesSpec, k8s_dynamic_client):
    """
    """
    redis_host = CACHE_HOST.format(tenant=jeeves.tenant)
    redis_port = 6379
    redis_tenant_password = generate_password(20)

    resource = get_resource(dynamic_client=k8s_dynamic_client, kind=ResourceKindEnum.Secret, api_version="v1")
    secret = base64.b64decode(
        k8s_dynamic_client.get(resource, namespace="test9", name="cache-secret").data.get("REDIS_PASSWORD")
    ).decode()

    redis = Redis(host=redis_host, port=redis_port, password=secret)

    response = redis.execute_command("namespace", "GET", ProductName)

    if response:
        redis.execute_command("namespace", "SET", ProductName, redis_tenant_password)
    else:
        redis.execute_command("namespace", "ADD", ProductName, redis_tenant_password)

    OnePasswordUtil(
        tenant=jeeves.tenant,
        server_item="application-config",
        vault="Jeeves",
    ).create_or_replace(key="redis_password", value=redis_tenant_password)


class RedisService(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self, jeeves: JeevesSpec) -> None:
        self.jeeves: JeevesSpec = jeeves
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Service, api_version="v1"
        )

    def payload(self):
        body = V1Service(
            api_version="v1",
            kind=ResourceKindEnum.Service.value,
            metadata=V1ObjectMeta(
                name="cache-new",
                namespace=self.jeeves.tenant,
                labels={"app": "cache-new", "kind": "redis"},
            ),
            spec=V1ServiceSpec(
                selector={"app": "cache-new", "kind": "redis"},
                type="ClusterIP",
                ports=[
                    V1ServicePort(
                        name="redis",
                        port=6379,
                        target_port=6379,
                    )
                ],
            )
        )

        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

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
                name=ProductName,
                namespace=self.jeeves.tenant
            )
        except NotFoundError as e:
            logger.error(f"Service {ProductName} not found in namespace {self.jeeves.tenant}")


class StateFullSet(K8sResourceBaseClass):
    """
    """
    def __init__(self, jeeves: JeevesSpec) -> None:
        self.jeeves: JeevesSpec = jeeves
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.StatefulSet, api_version="apps/v1"
        )
        self.name = "cache-new"

    def payload(self):
        body = V1StatefulSet(
            api_version="apps/v1",
            kind=ResourceKindEnum.StatefulSet.value,
            metadata=V1ObjectMeta(
                    namespace=self.jeeves.tenant,
                    name=self.name,
                    labels={"app": self.name}
            ),
            spec=V1StatefulSetSpec(
                replicas=1,
                selector={"matchLabels": {"app": self.name, "kind": "redis"}},
                service_name="cache-new-service",
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(
                        labels={"app": self.name, "kind": "redis"}
                    ),
                    spec=V1PodSpec(
                        image_pull_secrets=[V1LocalObjectReference(name="registrycred")],
                        containers=[
                            V1Container(
                                name=self.name,
                                image="apache/kvrocks:2.5.1",
                                args=["--requirepass", "$(REDIS_PASSWORD)", "--port", "6379"],
                                ports=[V1ContainerPort(container_port=6379, protocol="TCP")],
                                image_pull_policy="Always",
                                env=[
                                    V1EnvVar(
                                        name="REDIS_PASSWORD",
                                        value_from=V1EnvVarSource(
                                            secret_key_ref=V1SecretKeySelector(
                                                key="REDIS_PASSWORD",
                                                name="cache-secret"
                                            )
                                        )
                                    )
                                ]
                            )
                        ],
                    )
                ),
            )
        )

        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    async def put(self):
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource,
            body=self.payload(),
            field_manager="kubectl-client-side-apply"
        )
        RedisService(self.jeeves).put()
        # await asyncio.sleep(30)
        # create_product_namespace(self.jeeves, self.k8s_dynamic_client)

    def delete(self):
        """
        Don't delete StatefulSet
        """
        pass


if __name__ == "__main__":
    import asyncio
    jeeves = JeevesSpec(tenant="test9")
    asyncio.run(StateFullSet(jeeves).put())