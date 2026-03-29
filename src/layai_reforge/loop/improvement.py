from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from layai_reforge.archive.base import ArchiveStore
from layai_reforge.evaluators.composite import CompositeEvaluator
from layai_reforge.evaluators.registry import EvaluatorRegistry
from layai_reforge.gates.human import HumanGate, HumanDecision
from layai_reforge.loop.budget import GenerationBudget
from layai_reforge.loop.promotion import PromotionPolicy
from layai_reforge.loop.variants import VariantGenerator
from layai_reforge.models.artifacts import RunArtifact
from layai_reforge.models.program import ArchiveEntry, DomainTag, EvaluationReport, UnifiedProgram, Variant
from layai_reforge.sandbox.runner import SandboxConfig, SandboxRunner


@dataclass
class ImprovementLoopResult:
    generation_id: str
    variants: list[Variant] = field(default_factory=list)
    reports: list[EvaluationReport] = field(default_factory=list)
    promoted_program: UnifiedProgram | None = None
    archive_entry_ids: list[str] = field(default_factory=list)


class ImprovementLoop:
    """generate → sandbox/eval → select → archive → optional human promote."""

    def __init__(
        self,
        archive: ArchiveStore,
        sandbox: SandboxRunner,
        registry: EvaluatorRegistry,
        promotion: PromotionPolicy | None = None,
        human_gate: HumanGate | None = None,
        budget: GenerationBudget | None = None,
    ) -> None:
        self.archive = archive
        self.sandbox = sandbox
        self.registry = registry
        self.promotion = promotion or PromotionPolicy()
        self.human_gate = human_gate
        self.budget = budget or GenerationBudget()

    def run_generation(
        self,
        base: UnifiedProgram,
        variant_factory: Callable[[UnifiedProgram], list[Variant]],
        run_artifact_fn: Callable[[UnifiedProgram, Variant], RunArtifact],
        domain: DomainTag = DomainTag.GENERAL,
        aggregate_key: str = "aggregate",
    ) -> ImprovementLoopResult:
        gen_id = str(uuid.uuid4())
        result = ImprovementLoopResult(generation_id=gen_id)
        clock = self.budget.start_clock()
        variants = variant_factory(base)[: self.budget.max_variants]
        result.variants = variants

        best: tuple[float, UnifiedProgram, EvaluationReport, Variant] | None = None
        for v in variants:
            if self.budget.exceeded_time(clock):
                break
            child = VariantGenerator().materialize(base, v)
            artifact = run_artifact_fn(child, v)
            ev_ids = child.reforge_procedure.evaluator_ids
            evaluators = self.registry.resolve_many(ev_ids)
            if not evaluators:
                from layai_reforge.evaluators.math_eval import MathGradingEvaluator

                evaluators = [MathGradingEvaluator()]
            comp = CompositeEvaluator(evaluators, aggregate_key=aggregate_key)
            report = comp.evaluate(artifact)
            report.variant_id = v.id
            result.reports.append(report)

            agg = report.metrics.get(aggregate_key, 0.0)
            if best is None or agg > best[0]:
                best = (agg, child, report, v)

            entry = ArchiveEntry(
                program=child,
                scores=dict(report.metrics),
                parent_entry_ids=[],
                domain=domain,
            )
            eid = self.archive.add_entry(entry)
            result.archive_entry_ids.append(eid)

        if best and self.promotion.should_promote(best[2], aggregate_key=aggregate_key):
            prog, rep, var = best[1], best[2], best[3]
            if self.human_gate is not None:
                decision = self.human_gate.request_sync(var, rep)
                if decision != HumanDecision.APPROVE:
                    return result
            result.promoted_program = prog

        return result


def run_pytest_artifact(
    runner: SandboxRunner,
    workspace: Path,
    program: UnifiedProgram,
    variant: Variant,
) -> RunArtifact:
    """Helper: run pytest in sandbox workspace."""
    return runner.run_command(
        ["python3", "-m", "pytest", "-q"],
        cwd=workspace,
        variant_id=variant.id,
    )
