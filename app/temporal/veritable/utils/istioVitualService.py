import os

from loguru import logger

from app.core.settings import AppSettings, get_settings, ProductConfig
from app.temporal.common.istioVirtualService import IstioVirtualService
from app.temporal.veritable.utils.common import VeritableSpec, ProductName


async def create_istio_virtual_service(veritable: VeritableSpec):
    """
    Create istio virtual service
    """

    config: AppSettings = get_settings()
    product_config: ProductConfig = config.product_config.get(ProductName)

    environment: str = os.getenv("DEPLOYMENT", "integration").lower()

    istio_virtual_service = IstioVirtualService(
        namespace=veritable.tenant,
        product=ProductName,
    )

    http_list = []

    # http_api router
    http_api = {
        "name": "veritable-api",
        "route": [{
            "destination": {
                "host": f"veritable.{veritable.tenant}.svc.cluster.local",
                "port": {"number": 8000},
                "headers": {
                    "response": {
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

    await istio_virtual_service.create_or_replace(job_body)
    logger.info(f"Created istio virtual service for {veritable.tenant}")
