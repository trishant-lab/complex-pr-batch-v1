"""Hardening suite 06 — context / retry / redact smoke tests."""
from __future__ import annotations

import pytest


def test_build_context_suite_06():
    from app.cli.temporal.hardening.context import build_context, validate_context

    ctx = build_context("activity_6", tenant="acme-6", attempt=6)
    assert ctx["activity"] == "activity_6"
    assert ctx["tenant"] == "acme-6"
    assert validate_context(ctx) == []


def test_retry_policy_suite_06():
    from app.cli.temporal.hardening.retry import default_policies

    policies = default_policies()
    assert "transient_http" in policies
    assert policies["transient_http"].attempts >= 2


def test_redact_suite_06():
    from app.core.oncall_util.redact import redact_mapping

    raw = {"api_key": "secret-6", "url": "https://user:pass@example.com/x"}
    out = redact_mapping(raw)
    assert out["api_key"] == "***"
    assert "pass" not in out["url"]


def test_checklist_suite_06():
    from app.core.oncall_util.checklist import ProvisionChecklist

    cl = ProvisionChecklist(product="zsegment", tenant="t-6")
    cl.add("grafana", "Grafana board provisioned")
    cl.add("rocketmq", "RocketMQ topics ready")
    cl.mark("grafana", "ok")
    assert len(cl.incomplete()) == 1
