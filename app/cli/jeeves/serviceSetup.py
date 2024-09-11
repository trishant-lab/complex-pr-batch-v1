from kubernetes.client import V1ObjectMeta, V1Service, V1ServicePort, V1ServiceSpec
from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.jeeves.jeeves import JeevesSpec, ProductName
from app.cli.temporal.core.log import log_info


class Service(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self: "Service", jeeves: JeevesSpec) -> None:
        """
        Constructor
        """
        self.jeeves: JeevesSpec = jeeves
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Service, api_version="v1"
        )

    def payload(self: "Service") -> dict:
        """
        k8s resource payload
        """
        body = V1Service(
            api_version="v1",
            kind=ResourceKindEnum.Service.value,
            metadata=V1ObjectMeta(
                name=ProductName,
                namespace=self.jeeves.tenant,
                labels={"app": ProductName},
            ),
            spec=V1ServiceSpec(
                selector={"app": ProductName},
                type="ClusterIP",
                ports=[
                    V1ServicePort(
                        name="http",
                        port=8000,
                    )
                ],
            ),
        )

        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self: "Service") -> None:
        """
        k8s server side apply
        """
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource, body=self.payload(), field_manager="kubectl-client-side-apply"
        )
        log_info(f"Service {ProductName} created in namespace {self.jeeves.tenant}")

    def delete(self: "Service") -> None:
        """
        k8s delete resource
        """
        try:
            self.k8s_dynamic_client.delete(resource=self.resource, name=ProductName, namespace=self.jeeves.tenant)
        except NotFoundError:
            logger.error(f"Service {ProductName} not found in namespace {self.jeeves.tenant}")
