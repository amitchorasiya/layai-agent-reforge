from __future__ import annotations

import asyncio
from enum import Enum
from typing import Awaitable, Callable

from layai_reforge.models.program import EvaluationReport, Variant


class HumanDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    EDIT_REQUEST = "edit_request"


class HumanGate:
    """Async callback or sync auto-approve for tests."""

    def __init__(
        self,
        on_request: Callable[[Variant, EvaluationReport], Awaitable[HumanDecision]] | None = None,
        auto: HumanDecision | None = HumanDecision.APPROVE,
    ) -> None:
        self._on_request = on_request
        self._auto = auto

    async def request(self, variant: Variant, report: EvaluationReport) -> HumanDecision:
        if self._on_request:
            return await self._on_request(variant, report)
        return self._auto or HumanDecision.REJECT

    def request_sync(self, variant: Variant, report: EvaluationReport) -> HumanDecision:
        if self._on_request:
            return asyncio.run(self.request(variant, report))
        return self._auto or HumanDecision.REJECT
