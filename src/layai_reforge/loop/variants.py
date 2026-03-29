from __future__ import annotations

import itertools
import random
import uuid
from typing import Callable

from layai_reforge.models.program import ProgramPatchOp, UnifiedProgram, Variant
from layai_reforge.patches import apply_patches


class VariantGenerator:
    """Multiple strategies: template mutation, crossover, tool subset, evolutionary elite."""

    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)

    def propose_llm_patches(
        self,
        program: UnifiedProgram,
        llm_fn: Callable[[str], list[ProgramPatchOp]] | None,
        context: str = "",
    ) -> list[Variant]:
        if not llm_fn:
            return []
        prompt = program.reforge_agent.patch_proposal_prompt + "\n" + context
        patches = llm_fn(prompt)
        return [
            Variant(
                parent_program_id=program.id,
                parent_fingerprint=program.content_fingerprint(),
                patches=patches,
                generator_id="llm",
            )
        ]

    def paraphrase_prompt_variant(
        self,
        program: UnifiedProgram,
        suffix: str = " Be concise.",
    ) -> Variant:
        p = ProgramPatchOp(op="set_system_prompt", value=(program.task.system_prompt + suffix).strip())
        return Variant(
            parent_program_id=program.id,
            parent_fingerprint=program.content_fingerprint(),
            patches=[p],
            generator_id="paraphrase",
        )

    def tool_subset_variants(self, program: UnifiedProgram, max_variants: int = 4) -> list[Variant]:
        tools = program.task.tools
        if len(tools) <= 1:
            return []
        out: list[Variant] = []
        for i, combo in enumerate(itertools.combinations(tools, len(tools) - 1)):
            if i >= max_variants:
                break
            patches: list[ProgramPatchOp] = [
                ProgramPatchOp(op="remove_tool", value=t.name)
                for t in tools
                if t not in combo
            ]
            out.append(
                Variant(
                    parent_program_id=program.id,
                    parent_fingerprint=program.content_fingerprint(),
                    patches=patches,
                    generator_id="tool_subset",
                )
            )
        return out

    def crossover(
        self,
        a: UnifiedProgram,
        b: UnifiedProgram,
    ) -> Variant:
        """Merge reforge procedure evaluators from b into a (stepping-stone style)."""
        patches = [
            ProgramPatchOp(
                op="set_reforge_procedure_evaluators",
                value=list({*a.reforge_procedure.evaluator_ids, *b.reforge_procedure.evaluator_ids}),
            )
        ]
        return Variant(
            parent_program_id=a.id,
            parent_fingerprint=a.content_fingerprint(),
            patches=patches,
            generator_id="crossover",
        )

    def evolutionary_elite(
        self,
        population: list[UnifiedProgram],
        k: int = 2,
    ) -> list[Variant]:
        """Pick random pairs from elite slice (caller ranks population)."""
        out: list[Variant] = []
        elite = population[: max(k, 2)]
        for _ in range(min(k, len(elite))):
            x, y = self.rng.sample(elite, 2)
            out.append(self.crossover(x, y))
        return out

    def materialize(self, program: UnifiedProgram, variant: Variant) -> UnifiedProgram:
        child = apply_patches(program, variant.patches)
        child.id = str(uuid.uuid4())
        return child
