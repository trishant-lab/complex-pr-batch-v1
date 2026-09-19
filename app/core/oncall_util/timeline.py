"""Helpers for spreading review/event timestamps (training archives)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class MayWindow:
    open_at: datetime
    merge_at: datetime

    @classmethod
    def may_12(cls, open_hour: int = 6, merge_hour: int = 19) -> "MayWindow":
        open_at = datetime(2026, 5, 12, open_hour, 0, 0, tzinfo=timezone.utc)
        merge_at = datetime(2026, 5, 12, merge_hour, 45, 0, tzinfo=timezone.utc)
        return cls(open_at, merge_at)


def spread_events(n: int, window: MayWindow) -> list[datetime]:
    if n <= 0:
        return []
    span = (window.merge_at - window.open_at) / (n + 1)
    return [window.open_at + span * (i + 1) for i in range(n)]
