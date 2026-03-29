from __future__ import annotations

from layai_reforge.models.program import EvaluationReport


class PromotionPolicy:
    def __init__(
        self,
        min_aggregate_score: float = 0.8,
        require_all_evaluators_pass: bool = True,
    ) -> None:
        self.min_aggregate_score = min_aggregate_score
        self.require_all_evaluators_pass = require_all_evaluators_pass

    def should_promote(self, report: EvaluationReport, aggregate_key: str = "aggregate") -> bool:
        if self.require_all_evaluators_pass and not report.passed:
            return False
        agg = report.metrics.get(aggregate_key)
        if agg is None and report.metrics:
            agg = max(report.metrics.values())
        if agg is None:
            return report.passed
        return float(agg) >= self.min_aggregate_score
