from loguru import logger

from app.temporal.common.vmPodScrapper import VMPodScrapper
from app.temporal.veritable.utils.common import VeritableSpec, ProductName


async def vm_pod_scraper(veritable: VeritableSpec):
    """
    Scrape VM pods
    """
    vms_spec = {
        "namespaceSelector": {
            "matchNames": [veritable.tenant]
        },
        "podMetricsEndpoints": [{
            "path": "/metrics",
            "port": "http",
            "interval": "5s",
        }],
        "selector": {
            "matchLabels": {
                "app": ProductName
            }
        }
    }

    server_body = {
        "apiVersion": "operator.victoriametrics.com/v1beta1",
        "kind": "VMPodScrape",
        "metadata": {
            "name": "veritable-metrics",
            "namespace": veritable.tenant,
        },
        "spec": vms_spec
    }

    VMPodScrapper(
        namespace=veritable.tenant,
        name="veritable-metrics"
    ).create_or_replace(server_body)

    # create VM Pod Scrapper for temporal
    cli_vms_spec = {
        "namespaceSelector": {
            "matchNames": [veritable.tenant]
        },
        "podMetricsEndpoints": [{
            "path": "/metrics",
            "port": "http",
            "interval": "5s",
        }],
        "selector": {
            "matchLabels": {
                "app": "veritable-temporal"
            }
        }
    }

    cli_body = {
        "apiVersion": "operator.victoriametrics.com/v1beta1",
        "kind": "VMPodScrape",
        "metadata": {
            "name": "veritable-temporal-metrics",
            "namespace": veritable.tenant,
        },
        "spec": cli_vms_spec
    }

    VMPodScrapper(
        namespace=veritable.tenant,
        name="veritable-temporal-metrics"
    ).create_or_replace(cli_body)

    logger.info(f"VM Pod Scraper created for {veritable.tenant}")
