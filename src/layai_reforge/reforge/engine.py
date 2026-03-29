from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from layai_reforge.archive.base import ArchiveStore
from layai_reforge.memory.ledger import ReforgeMemory, RunLedger
from layai_reforge.models.program import (
    ReforgeProcedureSpec,
    ReforgeProcedureStep,
    ProgramPatchOp,
    UnifiedProgram,
)
from layai_reforge.patches import apply_patches


@dataclass
class ReforgeContext:
    base_program: UnifiedProgram
    archive: ArchiveStore
    ledger: RunLedger | None = None
    reforge_memory: ReforgeMemory | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReforgeProcedureResult:
    program: UnifiedProgram
    patches_applied: list[ProgramPatchOp] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)


@dataclass
class ReforgeNestedProcedureConfig:
    """Optional recursion / depth cap when editing the reforge procedure (stub)."""

    max_depth: int = 2


class ReforgeProcedureEngine:
    """Execute ReforgeProcedureSpec pipeline (plugin steps)."""

    def __init__(
        self,
        propose_patch_fn: Callable[[str, ReforgeContext], list[ProgramPatchOp]] | None = None,
    ) -> None:
        self.propose_patch_fn = propose_patch_fn

    def run(
        self,
        ctx: ReforgeContext,
        procedure: ReforgeProcedureSpec | None = None,
        nested: ReforgeNestedProcedureConfig | None = None,
        depth: int = 0,
    ) -> ReforgeProcedureResult:
        proc = procedure or ctx.base_program.reforge_procedure
        logs: list[str] = []
        program = ctx.base_program
        patches_applied: list[ProgramPatchOp] = []

        for step in proc.steps:
            if step.type == "retrieve_archive":
                k = int(step.params.get("k", 5))
                entries = ctx.archive.retrieve_for_reforge_context(k=k)
                ctx.extra["archive_snippets"] = [e.program.task.system_prompt[:500] for e in entries]
                logs.append(f"retrieve_archive k={k}")
            elif step.type == "propose_patch":
                if self.propose_patch_fn:
                    prompt = program.reforge_agent.patch_proposal_prompt
                    if ctx.reforge_memory:
                        prompt += "\n" + ctx.reforge_memory.text()
                    new_patches = self.propose_patch_fn(prompt, ctx)
                    for p in new_patches:
                        program = apply_patches(program, [p])
                        patches_applied.append(p)
                    logs.append(f"propose_patch n={len(new_patches)}")
            elif step.type == "static_lint":
                if len(program.task.system_prompt) > 100_000:
                    raise ValueError("system prompt too large")
                logs.append("static_lint ok")
            elif step.type == "simulate_rollout":
                logs.append("simulate_rollout skipped (hook in ImprovementLoop)")
            elif step.type == "aggregate_scores":
                logs.append("aggregate_scores hook")
            elif step.type == "apply_patch":
                logs.append("apply_patch noop in engine")
            elif step.type == "rollback":
                program = ctx.base_program
                patches_applied.clear()
                logs.append("rollback")
            elif step.type == "summarize_reforge_memory":
                if ctx.reforge_memory and ctx.ledger:
                    ctx.reforge_memory.append(ctx.ledger.recent_summary())
                logs.append("summarize_reforge_memory")
            else:
                logs.append(f"unknown step {step.type}")

        if nested and depth < nested.max_depth:
            logs.append(f"nested_reforge_procedure depth={depth} capped")

        return ReforgeProcedureResult(program=program, patches_applied=patches_applied, logs=logs)


def edit_reforge_procedure_with_patches(
    program: UnifiedProgram,
    patches: list[ProgramPatchOp],
) -> UnifiedProgram:
    """Apply patches that may include replace_reforge_procedure_steps."""
    return apply_patches(program, patches)
