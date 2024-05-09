from loguru import logger

from app.cli.k8s_util import get_dynamic_client, get_resource, ResourceKindEnum
from app.cli.veritable.common import VeritableSpec, ProductName


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
        "kind": ResourceKindEnum.VMPodScrape.value,
        "metadata": {
            "name": "veritable-metrics",
            "namespace": veritable.tenant,
        },
        "spec": vms_spec
    }

    k8s_dynamic_client = get_dynamic_client()
    resource = get_resource(
        dynamic_client=k8s_dynamic_client,
        kind=ResourceKindEnum.VMPodScrape,
        api_version="operator.victoriametrics.com/v1beta1"
    )

    body = k8s_dynamic_client.client.sanitize_for_serialization(server_body)

    k8s_dynamic_client.server_side_apply(
        resource=resource,
        body=body,
        field_manager="kubectl-client-side-apply"
    )

    # create VM Pod Scrapper for cli
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
                "app": "veritable-cli"
            }
        }
    }

    cli_body = {
        "apiVersion": "operator.victoriametrics.com/v1beta1",
        "kind": "VMPodScrape",
        "metadata": {
            "name": "veritable-cli-metrics",
            "namespace": veritable.tenant,
        },
        "spec": cli_vms_spec
    }

    cli_body = k8s_dynamic_client.client.sanitize_for_serialization(cli_body)

    k8s_dynamic_client.server_side_apply(
        resource=resource,
        body=cli_body,
        field_manager="kubectl-client-side-apply"
    )

    logger.info(f"VM Pod Scraper created for {veritable.tenant}")


async def vm_pod_scraper_delete(tenant_name: str):
    """
    Delete VM Pod Scraper
    """

    dynamic_client = get_dynamic_client()
    resource = get_resource(
        dynamic_client=dynamic_client,
        kind=ResourceKindEnum.VMPodScrape,
        api_version="operator.victoriametrics.com/v1beta1"
    )
    dynamic_client.delete(resource=resource, name="veritable-metrics", namespace=tenant_name)
    dynamic_client.delete(resource=resource, name="veritable-cli-metrics", namespace=tenant_name)
    logger.info(f"VM Pod Scraper deleted for {tenant_name}")
