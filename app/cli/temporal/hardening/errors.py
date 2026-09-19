"""Typed failures for Temporal hardening."""
from __future__ import annotations


class HardeningError(RuntimeError):
    """Base error for refuse-silent-fallback paths."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class MissingSettingError(HardeningError):
    def __init__(self, field: str):
        super().__init__("missing_setting", f"{field} is required")


class UnsafeFallbackError(HardeningError):
    def __init__(self, detail: str):
        super().__init__("unsafe_fallback", detail)


def classify_failure(exc: BaseException) -> str:
    """Map an exception to a coarse oncall class."""
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    if "timeout" in name or "timeout" in text:
        return "timeout"
    if "auth" in text or "401" in text or "403" in text:
        return "auth"
    if "not found" in text or "404" in text:
        return "not_found"
    if isinstance(exc, HardeningError):
        return exc.code
    return "unknown"
