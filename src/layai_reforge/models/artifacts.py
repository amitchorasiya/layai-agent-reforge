"""Runtime artifacts from task or sandbox runs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class RunArtifact(BaseModel):
    run_id: str
    variant_id: str | None = None
    program_fingerprint: str = ""
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    messages: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    latency_ms: float | None = None
    success: bool = True
    extra: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
