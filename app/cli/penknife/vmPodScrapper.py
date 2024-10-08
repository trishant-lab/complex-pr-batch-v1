from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.penknife.models.penknifespec import PenknifeSpec
from app.cli.penknife.penknife import ProductName
from app.cli.temporal.core.log import log_info


class VMPodScrapperServer(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self: "VMPodScrapperServer", penknife: PenknifeSpec) -> None:
        """
        Constructor
        """
        self.penknife: PenknifeSpec = penknife
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client,
            kind=ResourceKindEnum.VMPodScrape,
            api_version="operator.victoriametrics.com/v1beta1",
        )

    def payload(self: "VMPodScrapperServer") -> dict:
        """
        k8s resource payload
        """
        vms_spec = {
            "namespaceSelector": {"matchNames": [self.penknife.tenant]},
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
                "name": "penknife-metrics",
                "namespace": self.penknife.tenant,
            },
            "spec": vms_spec,
        }
        return self.k8s_dynamic_client.client.sanitize_for_serialization(body)

    def put(self: "VMPodScrapperServer") -> None:
        """
        k8s server side apply
        """
        self.k8s_dynamic_client.server_side_apply(
            resource=self.resource, body=self.payload(), field_manager="kubectl-client-side-apply", force_conflicts=True
        )
        log_info(f"VMPodScrapperServer created in namespace {self.penknife.tenant}")

    def delete(self: "VMPodScrapperServer") -> None:
        """
        k8s delete resource
        """
        try:
            self.k8s_dynamic_client.delete(resource=self.resource, name="penknife-metrics", namespace=self.penknife.tenant)
        except NotFoundError:
            logger.error(f"VMPodScrapperServer not found in namespace {self.penknife.tenant}")
