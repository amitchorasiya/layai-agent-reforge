from __future__ import annotations

import re

from layai_reforge.models.artifacts import RunArtifact
from layai_reforge.models.program import EvaluationReport


class RoboticsSimulationEvaluator:
    id = "robotics_sim"

    def __init__(self, score_regex: str = r"SCORE:\s*([0-9.+-eE]+)") -> None:
        self.score_regex = re.compile(score_regex)

    def evaluate(self, artifact: RunArtifact) -> EvaluationReport:
        text = artifact.stdout or artifact.stderr or ""
        m = self.score_regex.search(text)
        score = float(m.group(1)) if m else (1.0 if artifact.success else 0.0)
        score = min(1.0, max(0.0, score))
        return EvaluationReport(
            variant_id=artifact.variant_id or "",
            run_id=artifact.run_id,
            metrics={"score": score, "sim_reward": score},
            passed=artifact.success and score >= 0.5,
            stderr=artifact.stderr,
            evaluator_id=self.id,
        )
