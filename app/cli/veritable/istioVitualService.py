from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.veritable.common import ProductName
from app.cli.veritable.common import VeritableSpec
from app.core.settings import AppSettings, get_settings, VeritableSettings


class IstioVirtualService(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self, veritable: VeritableSpec) -> None:
        self.veritable: VeritableSpec = veritable
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client,
            kind=ResourceKindEnum.VirtualService,
            api_version="networking.istio.io/v1beta1"
        )
        self.config: AppSettings = get_settings()
        self.veritable_config: VeritableSettings = self.config.veritable
        self.env = self.config.env

    def payload(self):
        http_list = []

        # http_api router
        http_api = {
            "name": "veritable-api",
            "route": [{
                "destination": {
                    "host": f"veritable.{self.veritable.tenant}.svc.cluster.local",
                    "port": {"number": 8000},
                    # Todo "headers": {
                    #     "response": {
                    #         "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
                    #     }
                    # }
                }
            }],
            "match": [
                {"uri": {"regex": "^/api/v1/.*"}},
                {"uri": {"regex": "^/public/api/v1/.*"}},
                {"uri": {"prefix": "/docs"}},
                {"uri": {"prefix": "/redoc"}},
            ]
        }
        http_list.append(http_api)

        # http_redirect router
        if self.env != "production":
            http_redirect = {
                "name": "redirect",
                "match": [{
                    "uri": {"exact": "/"},
                }],
                "redirect": {
                    "uri": f"/{self.veritable.imageTag}/"
                }
            }
            http_list.append(http_redirect)

        # http_ui router
        http_ui = {
            "name": "veritable-ui",
            "route": [{
                "destination": {
                    "host": f"varnish-svc.varnish.svc.cluster.local",
                    "port": {"number": 80},

                }
            }],
            "match": [{
                "uri": {"prefix": "/"},
            }]
        }
        http_list.append(http_ui)

        body = {
            "apiVersion": "networking.istio.io/v1beta1",
            "kind": "VirtualService",
            "metadata": {
                "name": "veritable-vs",
                "namespace": self.veritable.tenant,
            },
            "spec": {
                "hosts": [
                    f"{self.veritable.tenant}.{self.veritable_config.domain_name}"
                ],
                "gateways": ["istio-system/istiogateway"],
                "http": http_list
            }
        }
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
                name=f"{ProductName}-vs",
                namespace=self.veritable.tenant
            )
        except NotFoundError as e:
            logger.error(f"VirtualService {ProductName}-vs not found in namespace {self.veritable.tenant}")
