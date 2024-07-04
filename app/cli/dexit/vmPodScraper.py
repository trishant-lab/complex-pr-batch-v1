from app.cli.temporal.core.log import log_info
from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.dexit.dexit import DexitSpec, ProductName
from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum


class VMPodScrapperServer(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self: "VMPodScrapperServer", dexit: DexitSpec) -> None:
        """
        Initialize class
        """
        self.dexit: DexitSpec = dexit
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client,
            kind=ResourceKindEnum.VMPodScrape,
            api_version="operator.victoriametrics.com/v1beta1",
        )

    def payload(self: "VMPodScrapperServer") -> dict:
        """
        Payload
        """
        vms_spec = {
            "namespaceSelector": {"matchNames": [self.dexit.tenant]},
            "podMetricsEndpoints": [
                {
                    "path": "/metrics",
                    "port": "http",
                    "interval": "5s",
                }
            ],
            "selector": {"matchLabels": {"app": ProductName}},
        }

        body = {
            "apiVersion": "operator.victoriametrics.com/v1beta1",
            "kind": ResourceKindEnum.VMPodScrape.value,
            "metadata": {
                "name": "dexit-metrics",
                "namespace": self.dexit.tenant,
            },
            "spec": vms_spec,
        }
        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self: "VMPodScrapperServer") -> None:
        """
        Put
        """
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource, body=self.payload(), field_manager="kubectl-client-side-apply"
        )
        log_info(message="VMPodScrapperServer dexit-metrics created successfully.")

    def delete(self: "VMPodScrapperServer") -> None:
        """
        Delete
        """
        try:
            self.k8s_dynamic_client.delete(resource=self.resource, name="dexit-metrics", namespace=self.dexit.tenant)
        except NotFoundError:
            logger.error(f"VMPodScrapperServer not found in namespace {self.dexit.tenant}")
