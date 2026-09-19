"""Redact secrets before pasting settings into Slack."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse, urlunparse

SECRET_KEYS = {
    "password", "token", "api_key", "apikey", "secret", "authorization",
    "private_key", "client_secret", "access_key",
}


def redact_url(url: str) -> str:
    try:
        parts = urlparse(url)
    except Exception:
        return "<unparseable-url>"
    netloc = parts.hostname or ""
    if parts.port:
        netloc = f"{netloc}:{parts.port}"
    return urlunparse((parts.scheme, netloc, parts.path, "", "", ""))


def redact_mapping(data: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in data.items():
        lk = str(k).lower()
        if any(s in lk for s in SECRET_KEYS):
            out[k] = "***"
        elif isinstance(v, dict):
            out[k] = redact_mapping(v)
        elif isinstance(v, str) and (v.startswith("http://") or v.startswith("https://")):
            out[k] = redact_url(v)
        else:
            out[k] = v
    return out
