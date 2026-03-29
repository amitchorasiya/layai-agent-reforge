from __future__ import annotations

from typing import Protocol

from layai_reforge.models.artifacts import RunArtifact
from layai_reforge.models.program import EvaluationReport


class Evaluator(Protocol):
    id: str

    def evaluate(self, artifact: RunArtifact) -> EvaluationReport:
        """Produce metrics and pass/fail from a run artifact."""
