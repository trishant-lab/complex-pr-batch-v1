from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.dexit.dexit import ProductName, DexitSpec
from app.core.settings import AppSettings, get_settings, DexitSettings


class IstioVirtualService(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self, dexit: DexitSpec) -> None:
        self.dexit: DexitSpec = dexit
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client,
            kind=ResourceKindEnum.VirtualService,
            api_version="networking.istio.io/v1beta1"
        )
        self.config: AppSettings = get_settings()
        self.dexit_config: DexitSettings = self.config.dexit
        self.env = self.config.env

    def payload(self):
        http_list = []

        # http_api router
        http_api = {
            "name": "dexit-api",
            "route": [{
                "destination": {
                    "host": f"dexit.{self.dexit.tenant}.svc.cluster.local",
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

        # http_log_collect router
        http_log_collect = {
            "name": "dexit-log-collect",
            "route": [{
                "destination": {
                    "host": f"grafana-agent.monitoring-system.svc.cluster.local",
                    "port": {"number": 12347},
                }
            }],
            "match": [{
                "uri": {"prefix": "/logcollect"},
            }],
            "rewrite": {
                "uri": "/collect"
            }
        }
        http_list.append(http_log_collect)

        # http analytics router
        http_analytics = {
            "name": "dexit-analytics",
            "route": [{
                "destination": {
                    "host": f"matomo-server.matomo.svc.cluster.local",
                    "port": {"number": 80},
                }
            }],
            "match": [{
                "uri": {"prefix": "/analytics/"},
            }],
            "rewrite": {
                "uri": "/"
            }
        }
        http_list.append(http_analytics)

        # http alerting router
        http_alerting = {
            "name": "dexit-alerting",
            "route": [{
                "destination": {
                    "host": f"api.novu.svc.cluster.local",
                    "port": {"number": 4000},
                }
            }],
            "match": [{
                "uri": {"prefix": "/alerting/"},
            }],
            "rewrite": {
                "uri": "/"
            }
        }
        http_list.append(http_alerting)

        # novu socket router
        novu_socket = {
            "name": "novu-socket",
            "route": [{
                "destination": {
                    "host": f"ws.novu.svc.cluster.local",
                    "port": {"number": 3002},
                }
            }],
            "match": [{
                "uri": {"prefix": "/socket.io/"},
            }]
        }
        http_list.append(novu_socket)

        # http_redirect router
        if self.env != "production":
            http_redirect = {
                "name": "redirect",
                "match": [{
                    "uri": {"exact": "/"},
                }],
                "redirect": {
                    "uri": f"/{self.dexit.imageTag}/"
                }
            }
            http_list.append(http_redirect)

        # http_ui router
        http_ui = {
            "name": "dexit-ui",
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
                "name": "dexit-vs",
                "namespace": self.dexit.tenant,
            },
            "spec": {
                "hosts": [
                    f"{self.dexit.tenant}.{self.dexit_config.domain_name}"
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
                namespace=self.dexit.tenant
            )
        except NotFoundError:
            logger.error(f"VirtualService {ProductName}-vs not found in namespace {self.dexit.tenant}")
