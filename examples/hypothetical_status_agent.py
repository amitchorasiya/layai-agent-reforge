"""
Hypothetical use case: evolve a **deployment health-check** agent.

The task agent is meant to print a single status line. We do not call an LLM here:
`run_artifact_fn` simulates execution by inspecting the materialized program's
`system_prompt`. Only a variant that adds an explicit contract ("print exactly …
HEALTH_OK") passes `MathGradingEvaluator`.

This exercises: `ImprovementLoop`, `VariantGenerator`, `SqliteArchiveStore`,
`EvaluatorRegistry`, and `PromotionPolicy`.

Run from repo root (with dev extras):

    pip install -e ".[dev]"
    python examples/hypothetical_status_agent.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Allow `python examples/hypothetical_status_agent.py` from repo root without pip install -e .
if __package__ is None:
    _repo = Path(__file__).resolve().parents[1]
    _src = _repo / "src"
    if str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

from layai_reforge import DomainTag, SqliteArchiveStore, UnifiedProgram
from layai_reforge.evaluators.math_eval import MathGradingEvaluator
from layai_reforge.evaluators.registry import EvaluatorRegistry
from layai_reforge.loop.improvement import ImprovementLoop, ImprovementLoopResult
from layai_reforge.loop.variants import VariantGenerator
from layai_reforge.models.artifacts import RunArtifact
from layai_reforge.models.program import ProgramPatchOp, ReforgeProcedureSpec, TaskAgentSpec, Variant
from layai_reforge.sandbox.runner import SandboxConfig, SandboxRunner

# Framed prompt — no magic words yet (simulated run will fail).
_BASE_PROMPT = """You are a deployment health monitor for a CI pipeline.
Respond with a single line describing service status when asked."""


def _simulate_health_run(child: UnifiedProgram, variant: Variant) -> RunArtifact:
    """Stub runtime: success only if the prompt encodes the expected contract."""
    prompt = child.task.system_prompt
    if "HEALTH_OK" in prompt and "exactly" in prompt.lower():
        stdout = "HEALTH_OK"
    else:
        stdout = "DEGRADED"
    return RunArtifact(
        run_id=f"sim-{variant.id[:8]}",
        variant_id=variant.id,
        stdout=stdout,
        stderr="",
        exit_code=0,
        success=True,
    )


def build_variants(program: UnifiedProgram) -> list[Variant]:
    vg = VariantGenerator(seed=42)
    paraphrase = vg.paraphrase_prompt_variant(program, suffix=" Be concise.")
    contract = Variant(
        parent_program_id=program.id,
        parent_fingerprint=program.content_fingerprint(),
        patches=[
            ProgramPatchOp(
                op="set_system_prompt",
                value=(
                    _BASE_PROMPT
                    + "\nWhen asked for status, print exactly one line: HEALTH_OK"
                ).strip(),
            )
        ],
        generator_id="contract_variant",
    )
    return [paraphrase, contract]


def run_status_agent_demo(workspace: Path) -> ImprovementLoopResult:
    archive = SqliteArchiveStore(workspace / "archive.sqlite")
    sandbox = SandboxRunner(SandboxConfig(workspace_root=workspace))
    reg = EvaluatorRegistry()
    reg.register(MathGradingEvaluator(golden_answer="HEALTH_OK"))

    program = UnifiedProgram(
        task=TaskAgentSpec(system_prompt=_BASE_PROMPT),
        reforge_procedure=ReforgeProcedureSpec(evaluator_ids=["math_grade"]),
    )

    def variant_factory(_p: UnifiedProgram) -> list[Variant]:
        return build_variants(_p)

    loop = ImprovementLoop(
        archive=archive,
        sandbox=sandbox,
        registry=reg,
        human_gate=None,
    )
    return loop.run_generation(
        program,
        variant_factory=variant_factory,
        run_artifact_fn=_simulate_health_run,
        domain=DomainTag.GENERAL,
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        res = run_status_agent_demo(root)
        promoted = res.promoted_program
        print("generation_id:", res.generation_id)
        print("variants_evaluated:", len(res.variants))
        print("archive_entries:", len(res.archive_entry_ids))
        print("promoted:", promoted is not None)
        if promoted:
            snippet = promoted.task.system_prompt[:120].replace("\n", " ")
            print("promoted_prompt_preview:", snippet + ("…" if len(promoted.task.system_prompt) > 120 else ""))


if __name__ == "__main__":
    main()
