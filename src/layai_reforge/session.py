"""High-level ReforgeSession API."""

from __future__ import annotations

from pathlib import Path

from layai_reforge.archive.base import ArchiveStore
from layai_reforge.evaluators.math_eval import MathGradingEvaluator
from layai_reforge.evaluators.registry import EvaluatorRegistry
from layai_reforge.gates.audit import AuditLogStore
from layai_reforge.gates.human import HumanDecision, HumanGate
from layai_reforge.loop.improvement import ImprovementLoop, ImprovementLoopResult
from layai_reforge.memory.ledger import ReforgeMemory, RunLedger
from layai_reforge.reforge.engine import ReforgeContext, ReforgeProcedureEngine, ReforgeProcedureResult
from layai_reforge.models.program import EvaluationReport, UnifiedProgram, Variant
from layai_reforge.program_io import load_program, save_program
from layai_reforge.sandbox.runner import SandboxConfig, SandboxRunner


class ReforgeSession:
    def __init__(
        self,
        program: UnifiedProgram,
        archive: ArchiveStore,
        sandbox_workspace: Path | None = None,
        audit_path: Path | None = None,
        human_gate: HumanGate | None = None,
    ) -> None:
        self.program = program
        self.archive = archive
        ws = sandbox_workspace or Path.cwd()
        self.sandbox = SandboxRunner(SandboxConfig(workspace_root=ws.resolve()))
        self.registry = EvaluatorRegistry()
        self.registry.register(MathGradingEvaluator())
        self.ledger = RunLedger()
        self.reforge_memory = ReforgeMemory()
        self._audit = AuditLogStore(audit_path or (ws / ".reforge" / "audit.sqlite"))
        self.human_gate = human_gate or HumanGate(auto=HumanDecision.APPROVE)

    def load_program_file(self, path: Path | str) -> None:
        self.program = load_program(path)

    def save_program_file(self, path: Path | str) -> None:
        save_program(self.program, path)

    def run_reforge_pipeline(
        self,
        propose_patch_fn=None,
    ) -> ReforgeProcedureResult:
        engine = ReforgeProcedureEngine(propose_patch_fn=propose_patch_fn)
        ctx = ReforgeContext(
            base_program=self.program,
            archive=self.archive,
            ledger=self.ledger,
            reforge_memory=self.reforge_memory,
        )
        return engine.run(ctx)

    def run_improvement_generation(self, loop: ImprovementLoop, **kwargs) -> ImprovementLoopResult:
        return loop.run_generation(self.program, **kwargs)

    def record_promotion_audit(
        self,
        variant: Variant,
        report: EvaluationReport,
        approved: bool,
        actor: str = "human",
    ) -> str:
        return self._audit.record_promotion(variant, report, approved=approved, actor=actor)
