from kubernetes.client import V1ObjectMeta, V1Service, V1ServicePort, V1ServiceSpec
from kubernetes.dynamic.exceptions import NotFoundError

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.temporal.core.log import log_info, log_error


class Service(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self: "Service", tenant: str, product: str, port: int) -> None:
        """
        Constructor
        """
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Service, api_version="v1"
        )
        self.tenant = tenant
        self.product = product
        self.port = port

    def payload(self: "Service") -> dict:
        """
        k8s resource payload
        """
        body = V1Service(
            api_version="v1",
            kind=ResourceKindEnum.Service.value,
            metadata=V1ObjectMeta(
                name=self.product,
                namespace=self.tenant,
                labels={"app": self.product},
            ),
            spec=V1ServiceSpec(
                selector={"app": self.product},
                type="ClusterIP",
                ports=[
                    V1ServicePort(
                        name="http",
                        port=self.port,
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
        log_info(f"Service {self.product} created in namespace {self.tenant}")

    def delete(self: "Service") -> None:
        """
        k8s delete resource
        """
        try:
            self.k8s_dynamic_client.delete(resource=self.resource, name=self.product, namespace=self.tenant)
        except NotFoundError:
            log_error(f"Service {self.product} not found in namespace {self.tenant}")
