"""Build structured logging / tracing context for Temporal activities."""
from __future__ import annotations

from typing import Any


def build_context(activity: str, tenant: str | None = None, **extra: Any) -> dict:
    """Return a JSON-serialisable context dict for logs and metrics."""
    ctx = {
        "activity": activity,
        "service": "launchpad",
        "layer": "temporal",
    }
    if tenant:
        ctx["tenant"] = tenant
    ctx.update(extra)
    return ctx


def merge_contexts(*parts: dict | None) -> dict:
    """Left-to-right merge; later keys win. Skips None."""
    out: dict = {}
    for part in parts:
        if not part:
            continue
        out.update(part)
    return out


KNOWN_CONTEXT_KEYS = [
    "activity",
    "tenant",
    "product",
    "env",
    "region",
    "datasource_uid",
    "grafana_url",
    "rocketmq_cluster",
    "workflow_id",
    "run_id",
    "attempt",
    "operator",
    "change_ticket",
    "correlation_id",
    "parent_span",
]


def validate_context(ctx: dict) -> list[str]:
    """Return missing recommended keys (non-fatal for callers)."""
    missing = []
    for key in ("activity", "service", "layer"):
        if key not in ctx:
            missing.append(key)
    return missing

