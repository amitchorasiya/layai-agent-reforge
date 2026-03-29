"""
Minimal outer loop: variant → trivial sandbox command → MathGradingEvaluator → archive.

Requires: pip install -e ..[dev] from repo root (or install package in env).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from layai_reforge import (
    DomainTag,
    SqliteArchiveStore,
    UnifiedProgram,
)
from layai_reforge.evaluators.math_eval import MathGradingEvaluator
from layai_reforge.evaluators.registry import EvaluatorRegistry
from layai_reforge.loop.improvement import ImprovementLoop
from layai_reforge.loop.variants import VariantGenerator
from layai_reforge.models.artifacts import RunArtifact
from layai_reforge.models.program import ReforgeAgentSpec, ReforgeProcedureSpec, TaskAgentSpec
from layai_reforge.sandbox.runner import SandboxConfig, SandboxRunner


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        archive = SqliteArchiveStore(root / "a.sqlite")
        sandbox = SandboxRunner(SandboxConfig(workspace_root=root))
        reg = EvaluatorRegistry()
        reg.register(MathGradingEvaluator(golden_answer="42"))

        program = UnifiedProgram(
            task=TaskAgentSpec(system_prompt="Answer: 42"),
            reforge_agent=ReforgeAgentSpec(),
            reforge_procedure=ReforgeProcedureSpec(evaluator_ids=["math_grade"]),
        )
        vg = VariantGenerator(seed=1)
        variants = [vg.paraphrase_prompt_variant(program)]

        def run_fn(child, variant):
            # Trivial: stdout must match golden for MathGradingEvaluator
            art = sandbox.run_command(["python3", "-c", "print(42)"], cwd=root, variant_id=variant.id)
            return RunArtifact(
                run_id=art.run_id,
                variant_id=variant.id,
                stdout="42",
                stderr=art.stderr,
                exit_code=0,
                success=True,
            )

        loop = ImprovementLoop(archive=archive, sandbox=sandbox, registry=reg)
        res = loop.run_generation(
            program,
            variant_factory=lambda p: variants,
            run_artifact_fn=run_fn,
            domain=DomainTag.MATH,
        )
        print("generation", res.generation_id, "promoted", res.promoted_program is not None)


if __name__ == "__main__":
    main()
