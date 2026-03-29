from __future__ import annotations

import re
from typing import Any

from layai_reforge.models.artifacts import RunArtifact
from layai_reforge.models.program import EvaluationReport


class MathGradingEvaluator:
    id = "math_grade"

    def __init__(
        self,
        golden_answer: str | None = None,
        normalize: bool = True,
    ) -> None:
        self.golden_answer = golden_answer
        self.normalize = normalize

    def evaluate(self, artifact: RunArtifact) -> EvaluationReport:
        text = (artifact.stdout or "").strip()
        if self.golden_answer is not None:
            a = _norm(text) if self.normalize else text
            b = _norm(self.golden_answer) if self.normalize else self.golden_answer
            ok = a == b or b in a
            score = 1.0 if ok else 0.0
        else:
            rubric = artifact.extra.get("math_rubric") or {}
            score = float(rubric.get("score", 1.0 if artifact.success else 0.0))
            ok = score >= 0.99
        return EvaluationReport(
            variant_id=artifact.variant_id or "",
            run_id=artifact.run_id,
            metrics={"score": score},
            passed=ok,
            evaluator_id=self.id,
        )


def _norm(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"\s+", "", s)
    return s
