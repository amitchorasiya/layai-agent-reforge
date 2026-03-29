"""Apply validated ProgramPatchOp sequences to UnifiedProgram."""

from __future__ import annotations

import copy
from datetime import datetime, timezone

from layai_reforge.models.program import (
    ReforgeProcedureSpec,
    ReforgeProcedureStep,
    ProgramPatchOp,
    TaskAgentSpec,
    ToolDescriptor,
    UnifiedProgram,
)


def apply_patches(program: UnifiedProgram, patches: list[ProgramPatchOp]) -> UnifiedProgram:
    """Return a new UnifiedProgram with patches applied (immutable-style)."""
    data = program.model_dump()
    task_dict = data["task"]
    reforge_agent_dict = data["reforge_agent"]
    proc_dict = data["reforge_procedure"]

    for p in patches:
        op = p.op
        if op == "set_system_prompt":
            task_dict["system_prompt"] = str(p.value)
        elif op == "add_tool":
            td = ToolDescriptor.model_validate(p.value)
            names = {t["name"] for t in task_dict["tools"]}
            if td.name not in names:
                task_dict["tools"].append(td.model_dump())
        elif op == "remove_tool":
            name = str(p.value)
            task_dict["tools"] = [t for t in task_dict["tools"] if t["name"] != name]
        elif op == "set_graph_config_key":
            key = p.path or ""
            if not key or ".." in key or key.startswith("/"):
                raise ValueError("invalid graph config key")
            task_dict["graph_config"] = dict(task_dict.get("graph_config") or {})
            task_dict["graph_config"][key] = copy.deepcopy(p.value)
        elif op == "set_reforge_patch_prompt":
            reforge_agent_dict["patch_proposal_prompt"] = str(p.value)
        elif op == "set_reforge_procedure_patch_prompt":
            reforge_agent_dict["reforge_procedure_patch_prompt"] = str(p.value)
        elif op == "replace_reforge_procedure_steps":
            steps = [ReforgeProcedureStep.model_validate(s) for s in p.value]
            proc_dict["steps"] = [s.model_dump() for s in steps]
        elif op == "set_reforge_procedure_evaluators":
            proc_dict["evaluator_ids"] = list(p.value or [])
        else:
            raise ValueError(f"unknown patch op: {op}")

    out = UnifiedProgram.model_validate(
        {
            **data,
            "task": TaskAgentSpec.model_validate(task_dict),
            "reforge_agent": type(program.reforge_agent).model_validate(reforge_agent_dict),
            "reforge_procedure": ReforgeProcedureSpec.model_validate(proc_dict),
            "updated_at": datetime.now(timezone.utc),
        }
    )
    return out
