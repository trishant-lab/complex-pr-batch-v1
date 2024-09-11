from app.cli.temporal.core.log import log_info
from kubernetes.client import V1ObjectMeta, V1Service, V1ServicePort, V1ServiceSpec
from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.dexit.dexit import DexitSpec, ProductName


class Service(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self: "Service", dexit: DexitSpec) -> None:
        """
        Constructor
        """
        self.dexit: DexitSpec = dexit
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client, kind=ResourceKindEnum.Service, api_version="v1"
        )

    def payload(self: "Service") -> dict:
        """
        Payload
        """
        body = V1Service(
            api_version="v1",
            kind=ResourceKindEnum.Service.value,
            metadata=V1ObjectMeta(
                name=ProductName,
                namespace=self.dexit.tenant,
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
        Put
        """
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource, body=self.payload(), field_manager="kubectl-client-side-apply"
        )
        log_info(message=f"Service {ProductName} created successfully.")

    def delete(self: "Service") -> None:
        """
        Delete
        """
        try:
            self.k8s_dynamic_client.delete(resource=self.resource, name=ProductName, namespace=self.dexit.tenant)
        except NotFoundError:
            logger.error(f"Service {ProductName} not found in namespace {self.dexit.tenant}")
