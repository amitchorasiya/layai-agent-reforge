from __future__ import annotations

from layai_reforge.models.artifacts import RunArtifact
from layai_reforge.models.program import EvaluationReport
from layai_reforge.evaluators.base import Evaluator


class CompositeEvaluator:
    """Weighted sum or Pareto-style aggregation."""

    def __init__(
        self,
        evaluators: list[Evaluator],
        weights: dict[str, float] | None = None,
        aggregate_key: str = "aggregate",
        pareto: bool = False,
    ) -> None:
        self.evaluators = evaluators
        self.weights = weights or {}
        self.aggregate_key = aggregate_key
        self.pareto = pareto

    @property
    def id(self) -> str:
        return "composite:" + ",".join(sorted(e.id for e in self.evaluators))

    def evaluate(self, artifact: RunArtifact) -> EvaluationReport:
        reports = [e.evaluate(artifact) for e in self.evaluators]
        metrics: dict[str, float] = {}
        for r in reports:
            for k, v in r.metrics.items():
                metrics[f"{r.evaluator_id}:{k}"] = v
        if self.pareto:
            agg = min((r.metrics.get("score", 0.0) for r in reports), default=0.0)
        else:
            agg = 0.0
            wsum = 0.0
            for r in reports:
                w = self.weights.get(r.evaluator_id, 1.0)
                agg += w * float(r.metrics.get("score", 1.0 if r.passed else 0.0))
                wsum += w
            agg = agg / wsum if wsum else 0.0
        metrics[self.aggregate_key] = agg
        passed = all(r.passed for r in reports)
        return EvaluationReport(
            variant_id=artifact.variant_id or "",
            run_id=artifact.run_id,
            metrics=metrics,
            passed=passed,
            stderr="\n".join(r.stderr for r in reports if r.stderr),
            evaluator_id=self.id,
        )
