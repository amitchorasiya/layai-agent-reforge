from __future__ import annotations

import time
from pydantic import BaseModel, Field


class GenerationBudget(BaseModel):
    max_variants: int = Field(default=8, ge=1)
    max_seconds: float = Field(default=600.0, ge=1.0)
    max_tokens: int | None = Field(default=None, ge=1)

    def start_clock(self) -> float:
        return time.monotonic()

    def exceeded_time(self, start: float) -> bool:
        return (time.monotonic() - start) >= self.max_seconds
