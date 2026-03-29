from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class RunLedgerEntry(BaseModel):
    thread_id: str
    task_id: str | None = None
    success: bool = True
    latency_ms: float | None = None
    tool_errors: int = 0
    human_corrections: int = 0
    extra: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RunLedger:
    """In-memory performance tracking; persist via archive reforge_memory_excerpt."""

    def __init__(self) -> None:
        self._entries: list[RunLedgerEntry] = []

    def record(self, entry: RunLedgerEntry) -> None:
        self._entries.append(entry)

    def recent_summary(self, n: int = 20) -> str:
        tail = self._entries[-n:]
        if not tail:
            return ""
        ok = sum(1 for e in tail if e.success)
        return f"last_{len(tail)}_runs success_rate={ok/len(tail):.2f}"


class ReforgeMemory:
    """Bounded blob injected into reforge-agent prompts."""

    def __init__(self, max_chars: int = 4000) -> None:
        self.max_chars = max_chars
        self._blob = ""

    def append(self, text: str) -> None:
        self._blob = (self._blob + "\n" + text).strip()
        if len(self._blob) > self.max_chars:
            self._blob = self._blob[-self.max_chars :]

    def text(self) -> str:
        return self._blob
