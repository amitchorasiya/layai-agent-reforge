from __future__ import annotations

from pathlib import Path

from layai_reforge.models.artifacts import RunArtifact
from layai_reforge.models.program import EvaluationReport


class PytestEvaluator:
    id = "pytest"

    def __init__(self, workspace: Path, pytest_args: list[str] | None = None) -> None:
        self.workspace = workspace
        self.pytest_args = pytest_args or ["-q"]

    def evaluate(self, artifact: RunArtifact) -> EvaluationReport:
        # In full flow, pytest runs via SandboxRunner; here score from artifact if pytest already ran
        score = 1.0 if artifact.success and artifact.exit_code == 0 else 0.0
        return EvaluationReport(
            variant_id=artifact.variant_id or "",
            run_id=artifact.run_id,
            metrics={"score": score, "tests_passed": score},
            passed=score >= 1.0,
            stderr=artifact.stderr,
            evaluator_id=self.id,
        )
