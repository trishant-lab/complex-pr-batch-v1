"""Metric name helpers for provision / oncall dashboards."""
from __future__ import annotations


def metric_name(product: str, action: str) -> str:
    """Stable Prometheus-style name: launchpad_<product>_<action>_total."""
    safe_product = product.replace("-", "_").replace(".", "_")
    safe_action = action.replace("-", "_").replace(".", "_")
    return f"launchpad_{safe_product}_{safe_action}_total"


def provision_counters(product: str) -> dict[str, str]:
    """Common counters every product activity should emit."""
    return {
        "started": metric_name(product, "provision_started"),
        "succeeded": metric_name(product, "provision_succeeded"),
        "failed": metric_name(product, "provision_failed"),
        "retried": metric_name(product, "provision_retried"),
    }
