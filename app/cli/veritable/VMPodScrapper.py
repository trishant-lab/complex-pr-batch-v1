from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.veritable.veritable import ProductName
from app.cli.veritable.models.veritableSpec import VeritableSpec


class VMPodScrapperServer(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self: "VMPodScrapperServer", veritable: VeritableSpec) -> None:
        """
        Initialize VMPodScrapperServer
        """
        self.veritable: VeritableSpec = veritable
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
            "namespaceSelector": {"matchNames": [self.veritable.tenant]},
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
                "name": "veritable-metrics",
                "namespace": self.veritable.tenant,
            },
            "spec": vms_spec,
        }
        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self: "VMPodScrapperServer") -> None:
        """
        Put VMPodScrapperServer
        """
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource, body=self.payload(), field_manager="kubectl-client-side-apply"
        )

    def delete(self: "VMPodScrapperServer") -> None:
        """
        Delete VMPodScrapperServer
        """
        try:
            self.k8s_dynamic_client.delete(
                resource=self.resource, name="veritable-metrics", namespace=self.veritable.tenant
            )
        except NotFoundError:
            logger.error(f"VMPodScrapperServer not found in namespace {self.veritable.tenant}")


class VMPodScrapperCli(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self: "VMPodScrapperCli", veritable: VeritableSpec) -> None:
        """
        Initialize VMPodScrapperCli
        """
        self.veritable: VeritableSpec = veritable
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client,
            kind=ResourceKindEnum.VMPodScrape,
            api_version="operator.victoriametrics.com/v1beta1",
        )

    def payload(self: "VMPodScrapperCli") -> dict:
        """
        Payload
        """
        cli_vms_spec = {
            "namespaceSelector": {"matchNames": [self.veritable.tenant]},
            "podMetricsEndpoints": [
                {
                    "path": "/metrics",
                    "port": "http",
                    "interval": "5s",
                }
            ],
            "selector": {"matchLabels": {"app": "veritable-cli"}},
        }

        body = {
            "apiVersion": "operator.victoriametrics.com/v1beta1",
            "kind": "VMPodScrape",
            "metadata": {
                "name": "veritable-cli-metrics",
                "namespace": self.veritable.tenant,
            },
            "spec": cli_vms_spec,
        }

        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self: "VMPodScrapperCli") -> None:
        """
        Put VMPodScrapperCli
        """
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource, body=self.payload(), field_manager="kubectl-client-side-apply"
        )

    def delete(self: "VMPodScrapperCli") -> None:
        """
        Delete VMPodScrapperCli
        """
        try:
            self.k8s_dynamic_client.delete(
                resource=self.resource, name="veritable-cli-metrics", namespace=self.veritable.tenant
            )
        except NotFoundError:
            logger.error(f"VMPodScrapperCli not found in namespace {self.veritable.tenant}")
