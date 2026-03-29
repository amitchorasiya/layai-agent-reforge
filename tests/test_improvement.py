import tempfile
from pathlib import Path

from layai_reforge import DomainTag, SqliteArchiveStore, UnifiedProgram
from layai_reforge.evaluators.math_eval import MathGradingEvaluator
from layai_reforge.evaluators.registry import EvaluatorRegistry
from layai_reforge.gates.human import HumanDecision, HumanGate
from layai_reforge.loop.improvement import ImprovementLoop
from layai_reforge.loop.variants import VariantGenerator
from layai_reforge.models.artifacts import RunArtifact
from layai_reforge.models.program import ReforgeProcedureSpec, TaskAgentSpec
from layai_reforge.sandbox.runner import SandboxConfig, SandboxRunner


def test_promotion_with_math_evaluator():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        archive = SqliteArchiveStore(root / "a.sqlite")
        sandbox = SandboxRunner(SandboxConfig(workspace_root=root))
        reg = EvaluatorRegistry()
        reg.register(MathGradingEvaluator(golden_answer="42"))
        program = UnifiedProgram(
            task=TaskAgentSpec(system_prompt="x"),
            reforge_procedure=ReforgeProcedureSpec(evaluator_ids=["math_grade"]),
        )
        vg = VariantGenerator(seed=0)
        variants = [vg.paraphrase_prompt_variant(program)]

        def run_fn(child, variant):
            return RunArtifact(
                run_id="r1",
                variant_id=variant.id,
                stdout="42",
                success=True,
            )

        loop = ImprovementLoop(archive=archive, sandbox=sandbox, registry=reg, human_gate=None)
        res = loop.run_generation(
            program,
            variant_factory=lambda p: variants,
            run_artifact_fn=run_fn,
            domain=DomainTag.MATH,
        )
        assert res.promoted_program is not None


def test_human_gate_rejects():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        archive = SqliteArchiveStore(root / "a.sqlite")
        sandbox = SandboxRunner(SandboxConfig(workspace_root=root))
        reg = EvaluatorRegistry()
        reg.register(MathGradingEvaluator(golden_answer="42"))
        program = UnifiedProgram(
            task=TaskAgentSpec(system_prompt="x"),
            reforge_procedure=ReforgeProcedureSpec(evaluator_ids=["math_grade"]),
        )
        vg = VariantGenerator(seed=0)
        variants = [vg.paraphrase_prompt_variant(program)]

        def run_fn(child, variant):
            return RunArtifact(
                run_id="r1",
                variant_id=variant.id,
                stdout="42",
                success=True,
            )

        loop = ImprovementLoop(
            archive=archive,
            sandbox=sandbox,
            registry=reg,
            human_gate=HumanGate(auto=HumanDecision.REJECT),
        )
        res = loop.run_generation(
            program,
            variant_factory=lambda p: variants,
            run_artifact_fn=run_fn,
            domain=DomainTag.MATH,
        )
        assert res.promoted_program is None
