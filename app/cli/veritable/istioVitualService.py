import os

from loguru import logger

from app.cli.k8s_util import get_dynamic_client, ResourceKindEnum, get_resource
from app.cli.veritable.common import VeritableSpec, ProductName
from app.core.settings import AppSettings, get_settings, ProductConfig


async def create_istio_virtual_service(veritable: VeritableSpec):
    """
    Create istio virtual service
    """

    config: AppSettings = get_settings()
    product_config: ProductConfig = config.product_config.get(ProductName)

    environment: str = os.getenv("DEPLOYMENT", "integration").lower()

    http_list = []

    # http_api router
    http_api = {
        "name": "veritable-api",
        "route": [{
            "destination": {
                "host": f"veritable.{veritable.tenant}.svc.cluster.local",
                "port": {"number": 8000},
                # "headers": {
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
    if environment != "production":
        http_redirect = {
            "name": "redirect",
            "match": [{
                "uri": {"exact": "/"},
            }],
            "redirect": {
                "uri": f"/{veritable.imageTag}/"
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

    job_body = {
        "apiVersion": "networking.istio.io/v1beta1",
        "kind": "VirtualService",
        "metadata": {
            "name": "veritable-vs",
            "namespace": veritable.tenant,
        },
        "spec": {
            "hosts": [
                f"{veritable.tenant}.{product_config.domain_name}"
            ],
            "gateways": ["istio-system/istiogateway"],
            "http": http_list
        }
    }

    k8s_dynamic_client = get_dynamic_client()
    resource = get_resource(
        dynamic_client=k8s_dynamic_client,
        kind=ResourceKindEnum.VirtualService,
        api_version="networking.istio.io/v1beta1"
    )

    body = k8s_dynamic_client.client.sanitize_for_serialization(job_body)

    k8s_dynamic_client.server_side_apply(resource=resource, body=body, field_manager="kubectl-client-side-apply")
    logger.info(f"Created istio virtual service for {veritable.tenant}")


async def delete_istio_virtual_service(tenant_name: str):
    """
    Delete istio virtual service
    """

    k8s_dynamic_client = get_dynamic_client()
    resource = get_resource(
        dynamic_client=k8s_dynamic_client,
        kind=ResourceKindEnum.VirtualService,
        api_version="networking.istio.io/v1beta1"
    )

    k8s_dynamic_client.delete(
        resource=resource, name=f"{ProductName}-vs", namespace=tenant_name
    )
