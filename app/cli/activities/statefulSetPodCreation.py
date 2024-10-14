from kubernetes.client import (
    V1StatefulSet,
    V1ObjectMeta,
    V1StatefulSetSpec,
    V1PodTemplateSpec,
    V1PodSpec,
    V1LocalObjectReference,
    V1Container,
    V1ResourceRequirements,
    V1SecurityContext,
    V1ContainerPort,
)
from kubernetes.dynamic.exceptions import NotFoundError

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.temporal.core.log import log_info, log_error
from app.core.settings import AppSettings, get_settings


class StatefulSetPodCreation(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(
        self: "StatefulSetPodCreation",
        tenant: str,
        name: str,
        docker_image: str,
        request_resource: dict,
        limit_resource: dict,
        container_port: int,
        volume_mounts: list,
        volumes: list,
        container_envs: list,
    ) -> None:
        """
        Constructor for DeploymentServer class
        """
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.StatefulSet, api_version="apps/v1"
        )

        self.config: AppSettings = get_settings()
        self.environment: str = self.config.env
        self.tenant = tenant
        self.name = name
        self.docker_image = docker_image
        self.request_resource = request_resource
        self.limit_resource = limit_resource
        self.container_port = container_port
        self.volume_mounts = volume_mounts
        self.volumes = volumes
        self.container_envs = container_envs

    def payload(self: "StatefulSetPodCreation") -> dict:
        """
        k8s resource payload
        """
        body = V1StatefulSet(
            api_version="apps/v1",
            kind=ResourceKindEnum.StatefulSet.value,
            metadata=V1ObjectMeta(namespace=self.tenant, name=self.name, labels={"app": self.name}),
            spec=V1StatefulSetSpec(
                replicas=1,
                selector={"matchLabels": {"app": self.name}},
                service_name=f"{self.name}-service",
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(labels={"app": self.name}),
                    spec=V1PodSpec(
                        image_pull_secrets=[V1LocalObjectReference(name="registrycred")],
                        node_selector={"app": "314e"},
                        containers=[
                            V1Container(
                                name=self.name,
                                image=self.docker_image,
                                image_pull_policy="Always",
                                resources=V1ResourceRequirements(
                                    requests=self.request_resource, limits=self.limit_resource
                                ),
                                security_context=V1SecurityContext(privileged=True),
                                ports=[
                                    V1ContainerPort(name="http", protocol="TCP", container_port=self.container_port)
                                ],
                                volume_mounts=self.volume_mounts,
                                env=self.container_envs,
                            )
                        ],
                        volumes=self.volumes,
                    ),
                ),
            ),
        )

        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self: "StatefulSetPodCreation") -> None:
        """
        k8s server side apply
        """
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource, body=self.payload(), field_manager="kubectl-client-side-apply", force_conflicts=True
        )
        log_info(f"StatefulSetPodCreation created in namespace {self.tenant}")

    def delete(self: "StatefulSetPodCreation") -> None:
        """
        k8s delete resource
        """
        try:
            self.k8s_dynamic_client.delete(resource=self.resource, name=self.name, namespace=self.tenant)
        except NotFoundError:
            log_error(f"StatefulSetPodCreation {self.name} not found in namespace {self.tenant}")
