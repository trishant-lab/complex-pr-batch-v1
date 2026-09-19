"""Retry policy catalogue for Temporal activities."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    name: str
    attempts: int
    backoff_seconds: int
    non_retryable: tuple[str, ...] = ()

    def describe(self) -> str:
        return (
            f"{self.name}: attempts={self.attempts} "
            f"backoff={self.backoff_seconds}s "
            f"non_retryable={','.join(self.non_retryable) or '-'}"
        )


def default_policies() -> dict[str, RetryPolicy]:
    return {
        "transient_http": RetryPolicy("transient_http", 5, 8, ("HardeningError",)),
        "dependency_warmup": RetryPolicy("dependency_warmup", 3, 20),
        "idempotent_create": RetryPolicy("idempotent_create", 2, 5, ("UnsafeFallbackError",)),
        "settings_read": RetryPolicy("settings_read", 4, 3),
    }
