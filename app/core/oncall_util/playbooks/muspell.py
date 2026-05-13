"""Oncall playbook for muspell provisioning."""
from __future__ import annotations


PRODUCT = "muspell"


def prechecks() -> list[str]:
    return [
        "settings snapshot redacted",
        "required fields present",
        "dependency health OK",
        "correlation id allocated",
    ]


def steps() -> list[str]:
    return [
        "1. Load product settings and redact for Slack",
        "2. Confirm required fields via require_settings_field",
        "3. Open Temporal workflow with correlation id",
        "4. Watch provision counters for started/succeeded/failed",
        "5. Refuse silent resource-name reuse on retry",
        "6. Update provision checklist and close change ticket",
    ]


def rollback() -> list[str]:
    return [
        "re-run with same correlation id",
        "do not invent a parallel tenant resource name",
        "capture classify_failure() code in the incident doc",
    ]


def dashboards() -> list[str]:
    return [f"launchpad-{PRODUCT}", "temporal-worker", "grafana-provision"]


def as_dict() -> dict:
    return {
        "product": PRODUCT,
        "prechecks": prechecks(),
        "steps": steps(),
        "rollback": rollback(),
        "dashboards": dashboards(),
    }
