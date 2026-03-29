from __future__ import annotations

import json
import re
from typing import Any

from layai_reforge.models.artifacts import RunArtifact
from layai_reforge.models.program import EvaluationReport


class PaperRubricEvaluator:
    id = "paper_rubric"

    def __init__(self, rubric: dict[str, Any], judge_output_key: str = "rubric_scores") -> None:
        self.rubric = rubric
        self.judge_output_key = judge_output_key

    def evaluate(self, artifact: RunArtifact) -> EvaluationReport:
        raw = artifact.extra.get(self.judge_output_key)
        if raw is None:
            text = artifact.stdout or ""
            raw = _parse_json_from_text(text)
        scores = _score_rubric(self.rubric, raw or {})
        agg = sum(scores.values()) / max(len(scores), 1) if scores else 0.0
        return EvaluationReport(
            variant_id=artifact.variant_id or "",
            run_id=artifact.run_id,
            metrics={"score": agg, **{f"criterion_{k}": v for k, v in scores.items()}},
            passed=agg >= 0.7,
            raw_judge_output=raw if isinstance(raw, dict) else None,
            evaluator_id=self.id,
        )


def _parse_json_from_text(text: str) -> dict[str, Any] | None:
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        return json.loads(m.group())
    except json.JSONDecodeError:
        return None


def _score_rubric(rubric: dict[str, Any], judge: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for key, spec in rubric.items():
        if isinstance(spec, dict) and "weight" in spec:
            w = float(spec["weight"])
            val = float(judge.get(key, 0.0))
            out[key] = min(1.0, max(0.0, val)) * w
        else:
            val = float(judge.get(key, 0.0))
            out[key] = min(1.0, max(0.0, val))
    return out
