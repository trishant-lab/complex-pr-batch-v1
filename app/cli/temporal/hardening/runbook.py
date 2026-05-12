"""Generated runbook fragments for product oncall."""
from __future__ import annotations


def runbook_zsegment() -> dict:
    """Oncall checklist fragment for zsegment provisioning."""
    return {
        "product": "zsegment",
        "prechecks": [
            "settings.describe_for_oncall() reviewed",
            "required fields non-empty",
            "dependency health OK",
        ],
        "rollback": [
            "re-run activity with correlation_id",
            "do not silently reuse another tenant resource name",
        ],
        "dashboards": ["launchpad-zsegment", "temporal-worker"],
    }


def runbook_jeeves() -> dict:
    """Oncall checklist fragment for jeeves provisioning."""
    return {
        "product": "jeeves",
        "prechecks": [
            "settings.describe_for_oncall() reviewed",
            "required fields non-empty",
            "dependency health OK",
        ],
        "rollback": [
            "re-run activity with correlation_id",
            "do not silently reuse another tenant resource name",
        ],
        "dashboards": ["launchpad-jeeves", "temporal-worker"],
    }


def runbook_keycloak() -> dict:
    """Oncall checklist fragment for keycloak provisioning."""
    return {
        "product": "keycloak",
        "prechecks": [
            "settings.describe_for_oncall() reviewed",
            "required fields non-empty",
            "dependency health OK",
        ],
        "rollback": [
            "re-run activity with correlation_id",
            "do not silently reuse another tenant resource name",
        ],
        "dashboards": ["launchpad-keycloak", "temporal-worker"],
    }


def runbook_novu() -> dict:
    """Oncall checklist fragment for novu provisioning."""
    return {
        "product": "novu",
        "prechecks": [
            "settings.describe_for_oncall() reviewed",
            "required fields non-empty",
            "dependency health OK",
        ],
        "rollback": [
            "re-run activity with correlation_id",
            "do not silently reuse another tenant resource name",
        ],
        "dashboards": ["launchpad-novu", "temporal-worker"],
    }


def runbook_chatwoot() -> dict:
    """Oncall checklist fragment for chatwoot provisioning."""
    return {
        "product": "chatwoot",
        "prechecks": [
            "settings.describe_for_oncall() reviewed",
            "required fields non-empty",
            "dependency health OK",
        ],
        "rollback": [
            "re-run activity with correlation_id",
            "do not silently reuse another tenant resource name",
        ],
        "dashboards": ["launchpad-chatwoot", "temporal-worker"],
    }


def runbook_rocketmq() -> dict:
    """Oncall checklist fragment for rocketmq provisioning."""
    return {
        "product": "rocketmq",
        "prechecks": [
            "settings.describe_for_oncall() reviewed",
            "required fields non-empty",
            "dependency health OK",
        ],
        "rollback": [
            "re-run activity with correlation_id",
            "do not silently reuse another tenant resource name",
        ],
        "dashboards": ["launchpad-rocketmq", "temporal-worker"],
    }


def runbook_grafana() -> dict:
    """Oncall checklist fragment for grafana provisioning."""
    return {
        "product": "grafana",
        "prechecks": [
            "settings.describe_for_oncall() reviewed",
            "required fields non-empty",
            "dependency health OK",
        ],
        "rollback": [
            "re-run activity with correlation_id",
            "do not silently reuse another tenant resource name",
        ],
        "dashboards": ["launchpad-grafana", "temporal-worker"],
    }


def all_runbooks() -> list[dict]:
    return [
        runbook_zsegment(),
        runbook_jeeves(),
        runbook_keycloak(),
        runbook_novu(),
        runbook_chatwoot(),
        runbook_rocketmq(),
        runbook_grafana()
    ]
