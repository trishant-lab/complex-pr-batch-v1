"""Provision checklist model for oncall handoff."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CheckItem:
    key: str
    label: str
    done: bool = False
    notes: str = ""


@dataclass
class ProvisionChecklist:
    product: str
    tenant: str
    items: list[CheckItem] = field(default_factory=list)

    def add(self, key: str, label: str) -> None:
        self.items.append(CheckItem(key=key, label=label))

    def mark(self, key: str, notes: str = "") -> None:
        for item in self.items:
            if item.key == key:
                item.done = True
                item.notes = notes
                return
        raise KeyError(key)

    def incomplete(self) -> list[CheckItem]:
        return [i for i in self.items if not i.done]

    def as_markdown(self) -> str:
        lines = [f"# {self.product} / {self.tenant}", ""]
        for item in self.items:
            mark = "x" if item.done else " "
            extra = f" — {item.notes}" if item.notes else ""
            lines.append(f"- [{mark}] {item.label}{extra}")
        return "\n".join(lines)
