"""Slack paste helpers for oncall."""
from __future__ import annotations

from .redact import redact_mapping


def settings_slack_block(product: str, settings: dict) -> str:
    safe = redact_mapping(settings)
    lines = [f"*{product} settings (redacted)*", "```"]
    for k in sorted(safe):
        lines.append(f"{k}={safe[k]}")
    lines.append("```")
    return "\n".join(lines)


def failure_slack_block(activity: str, error: str, correlation_id: str) -> str:
    return (
        f":red_circle: `{activity}` failed\n"
        f"correlation_id=`{correlation_id}`\n"
        f"```{error[:500]}```"
    )
