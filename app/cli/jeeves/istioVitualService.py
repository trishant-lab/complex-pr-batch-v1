from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.jeeves.common import ProductName, JeevesSpec
from app.core.settings import AppSettings, get_settings, JeevesSettings


class IstioVirtualService(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self, jeeves: JeevesSpec) -> None:
        self.jeeves: JeevesSpec = jeeves
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client,
            kind=ResourceKindEnum.VirtualService,
            api_version="networking.istio.io/v1beta1"
        )
        self.config: AppSettings = get_settings()
        self.jeeves_config: JeevesSettings = self.config.jeeves
        self.env = self.config.env
        self.image_tag = "sprint" if self.env == "integration" else "production"

    def payload(self):
        http_list = []

        # http_api router
        http_api = {
            "name": "jeeves-api",
            "route": [{
                "destination": {
                    "host": f"jeeves.{self.jeeves.tenant}.svc.cluster.local",
                    "port": {"number": 8000},
                },
                "headers": {
                    "response": {
                        "add": {
                            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
                        }
                    }
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
                    "uri": f"/{self.image_tag}/"
                }
            }
            http_list.append(http_redirect)

        # http_ui router
        http_ui = {
            "name": "jeeves-ui",
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
                "name": "jeeves-vs",
                "namespace": self.jeeves.tenant,
            },
            "spec": {
                "hosts": [
                    f"{self.jeeves.tenant}.{self.jeeves_config.domain_name}"
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
                namespace=self.jeeves.tenant
            )
        except NotFoundError:
            logger.error(f"VirtualService {ProductName}-vs not found in namespace {self.jeeves.tenant}")
