from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.temporal.core.log import log_info


class IstioVirtualService(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(
        self: "IstioVirtualService",
        payload: list,
        tenant: str,
        domain_name: str,
        product: str,
        service_name: str | None = None,
        host: str | None = None,
    ) -> None:
        """
        Constructor for IstioVirtualService
        """
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client,
            kind=ResourceKindEnum.VirtualService,
            api_version="networking.istio.io/v1beta1",
        )
        self.http_list = payload
        self.tenant = tenant
        self.domain_name = domain_name
        self.product_name = product
        self.service_name = service_name if service_name else f"{self.product_name.lower()}-vs"
        self.host = host if host else f"{self.tenant}.{self.domain_name}"

    def payload(self: "IstioVirtualService") -> dict:
        """
        Payload
        """
        body = {
            "apiVersion": "networking.istio.io/v1beta1",
            "kind": "VirtualService",
            "metadata": {
                "name": self.service_name,
                "namespace": self.tenant,
            },
            "spec": {
                "hosts": [self.host],
                "gateways": ["istio-system/istiogateway"],
                "http": self.http_list,
            },
        }
        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self: "IstioVirtualService") -> None:
        """
        Put VirtualService
        """
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource, body=self.payload(), field_manager="kubectl-client-side-apply"
        )
        log_info(f"VirtualService {self.service_name} created in namespace {self.tenant}")

    def delete(self: "IstioVirtualService") -> None:
        """
        Delete VirtualService
        """
        try:
            self.k8s_dynamic_client.delete(resource=self.resource, name=f"{self.service_name}", namespace=self.tenant)
        except NotFoundError:
            logger.error(f"VirtualService {self.service_name} not found in namespace {self.tenant}")
