from kubernetes.dynamic.exceptions import NotFoundError
from loguru import logger

from app.cli.k8sResourceBaseClass import K8sResourceBaseClass
from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.penknife.models.penknifespec import PenknifeSpec
from app.cli.penknife.penknife import ProductName
from app.cli.temporal.core.log import log_info
from app.core.settings import AppSettings, PenknifeSettings, get_settings


class IstioVirtualService(K8sResourceBaseClass):
    """
    Namespace class
    """

    def __init__(self: "IstioVirtualService", penknife: PenknifeSpec) -> None:
        """
        Constructor for IstioVirtualService
        """
        self.penknife: PenknifeSpec = penknife
        self.k8s_dynamic_client = get_dynamic_client()
        self.resource = get_resource(
            dynamic_client=self.k8s_dynamic_client,
            kind=ResourceKindEnum.VirtualService,
            api_version="networking.istio.io/v1beta1",
        )
        self.config: AppSettings = get_settings()
        self.penknife_config: PenknifeSettings = self.config.penknife
        self.env = self.config.env
        self.image_tag = "sprint" if self.env == "integration" else "production"

    # TODO: Verify this
    def payload(self: "IstioVirtualService") -> dict:
        """
        Payload
        """
        http_list = []

        # http_api router
        http_api = {
            "name": "penknife-api",
            "route": [
                {
                    "destination": {
                        "host": f"penknife.{self.penknife.tenant}.svc.cluster.local",
                        "port": {"number": 8000},
                    },
                    "headers": {
                        "response": {
                            "add": {
                                "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
                            }
                        }
                    },
                }
            ],
            "match": [
                {"uri": {"regex": "^/api/v1/.*"}},
                {"uri": {"regex": "^/public/api/v1/.*"}},
                {"uri": {"prefix": "/docs"}},
                {"uri": {"prefix": "/redoc"}},
            ],
        }
        http_list.append(http_api)

        # http_log_collect router
        http_log_collect = {
            "name": "penknife-log-collect",
            "route": [
                {
                    "destination": {
                        "host": "grafana-agent.monitoring-system.svc.cluster.local",
                        "port": {"number": 12347},
                    }
                }
            ],
            "match": [
                {
                    "uri": {"prefix": "/logcollect"},
                }
            ],
            "rewrite": {"uri": "/collect"},
        }
        http_list.append(http_log_collect)

        # # http analytics router
        # http_analytics = {
        #     "name": "penknife-analytics",
        #     "route": [
        #         {
        #             "destination": {
        #                 "host": "matomo-server.matomo.svc.cluster.local",
        #                 "port": {"number": 80},
        #             }
        #         }
        #     ],
        #     "match": [
        #         {
        #             "uri": {"prefix": "/analytics/"},
        #         }
        #     ],
        #     "rewrite": {"uri": "/"},
        # }
        # http_list.append(http_analytics)

        # http alerting router
        http_alerting = {
            "name": "penknife-alerting",
            "route": [
                {
                    "destination": {
                        "host": "api.novu.svc.cluster.local",
                        "port": {"number": 4000},
                    }
                }
            ],
            "match": [
                {
                    "uri": {"prefix": "/alerting/"},
                }
            ],
            "rewrite": {"uri": "/"},
        }
        http_list.append(http_alerting)

        # novu socket router
        novu_socket = {
            "name": "novu-socket",
            "route": [
                {
                    "destination": {
                        "host": "ws.novu.svc.cluster.local",
                        "port": {"number": 3002},
                    }
                }
            ],
            "match": [
                {
                    "uri": {"prefix": "/socket.io/"},
                }
            ],
        }
        http_list.append(novu_socket)

        # http_redirect router
        if self.env != "production":
            http_redirect = {
                "name": "redirect",
                "match": [
                    {
                        "uri": {"exact": "/"},
                    }
                ],
                "redirect": {"uri": f"/{self.image_tag}/"},
            }
            http_list.append(http_redirect)

        # http_ui router
        http_ui = {
            "name": "penknife-ui",
            "route": [
                {
                    "destination": {
                        "host": "varnish-svc.varnish.svc.cluster.local",
                        "port": {"number": 80},
                    }
                }
            ],
            "match": [
                {
                    "uri": {"prefix": "/"},
                }
            ],
        }
        http_list.append(http_ui)

        body = {
            "apiVersion": "networking.istio.io/v1beta1",
            "kind": "VirtualService",
            "metadata": {
                "name": "penknife-vs",
                "namespace": self.penknife.tenant,
            },
            "spec": {
                "hosts": [f"{self.penknife.tenant}.{self.penknife_config.domain_name}"],
                "gateways": ["istio-system/istiogateway"],
                "http": http_list,
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
        log_info(f"VirtualService {ProductName}-vs created in namespace {self.penknife.tenant}")

    def delete(self: "IstioVirtualService") -> None:
        """
        Delete VirtualService
        """
        try:
            self.k8s_dynamic_client.delete(
                resource=self.resource, name=f"{ProductName}-vs", namespace=self.penknife.tenant
            )
        except NotFoundError:
            logger.error(f"VirtualService {ProductName}-vs not found in namespace {self.penknife.tenant}")
