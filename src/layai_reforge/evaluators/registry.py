from __future__ import annotations

from layai_reforge.evaluators.base import Evaluator


class EvaluatorRegistry:
    def __init__(self) -> None:
        self._by_id: dict[str, Evaluator] = {}

    def register(self, ev: Evaluator) -> None:
        self._by_id[ev.id] = ev

    def get(self, evaluator_id: str) -> Evaluator | None:
        return self._by_id.get(evaluator_id)

    def resolve_many(self, ids: list[str]) -> list[Evaluator]:
        out: list[Evaluator] = []
        for i in ids:
            e = self.get(i)
            if e:
                out.append(e)
        return out
