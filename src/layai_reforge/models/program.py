"""Core Pydantic models: unified program, variants, evaluation, archive entries."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class DomainTag(str, Enum):
    CODING = "coding"
    PAPER_REVIEW = "paper_review"
    ROBOTICS = "robotics"
    MATH = "math"
    GENERAL = "general"


class ToolDescriptor(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    json_schema: dict[str, Any] | None = None


class TaskAgentSpec(BaseModel):
    system_prompt: str = ""
    tools: list[ToolDescriptor] = Field(default_factory=list)
    graph_builder_ref: str | None = Field(
        default=None,
        description="Import path to factory, e.g. mypkg.graph:build_graph",
    )
    graph_config: dict[str, Any] = Field(default_factory=dict)
    model_hint: str | None = None
    max_steps: int = Field(default=50, ge=1, le=10_000)
    tool_budget: int = Field(default=100, ge=0, le=100_000)


class ReforgeAgentSpec(BaseModel):
    """Prompts for the reforge agent (proposes patches to the unified program)."""

    patch_proposal_prompt: str = ""
    reforge_procedure_patch_prompt: str = ""
    structured_output_schema: dict[str, Any] | None = None


class ReforgeProcedureStep(BaseModel):
    """Declarative pipeline step id; executor maps to plugins."""

    type: Literal[
        "retrieve_archive",
        "propose_patch",
        "static_lint",
        "simulate_rollout",
        "aggregate_scores",
        "apply_patch",
        "rollback",
        "summarize_reforge_memory",
    ]
    params: dict[str, Any] = Field(default_factory=dict)


class ReforgeProcedureSpec(BaseModel):
    steps: list[ReforgeProcedureStep] = Field(
        default_factory=lambda: [
            ReforgeProcedureStep(type="retrieve_archive", params={"k": 5}),
            ReforgeProcedureStep(type="propose_patch", params={}),
            ReforgeProcedureStep(type="static_lint", params={}),
            ReforgeProcedureStep(type="aggregate_scores", params={}),
        ]
    )
    evaluator_ids: list[str] = Field(default_factory=list)
    stop_after_seconds: float | None = Field(default=None, ge=0)
    max_variants_per_generation: int = Field(default=8, ge=1, le=10_000)


class ProgramPatchOp(BaseModel):
    op: Literal[
        "set_system_prompt",
        "add_tool",
        "remove_tool",
        "set_graph_config_key",
        "set_reforge_patch_prompt",
        "set_reforge_procedure_patch_prompt",
        "replace_reforge_procedure_steps",
        "set_reforge_procedure_evaluators",
    ]
    path: str | None = None
    value: Any = None

    @model_validator(mode="after")
    def check_value(self) -> ProgramPatchOp:
        if self.op == "set_system_prompt" and not isinstance(self.value, str):
            raise ValueError("set_system_prompt requires string value")
        if self.op == "add_tool" and self.value is not None:
            if not isinstance(self.value, dict):
                raise ValueError("add_tool value must be a tool descriptor dict")
        if self.op == "remove_tool" and not isinstance(self.value, str):
            raise ValueError("remove_tool requires tool name string in value")
        if self.op == "set_graph_config_key" and self.path is None:
            raise ValueError("set_graph_config_key requires path (key name)")
        if self.op == "replace_reforge_procedure_steps" and not isinstance(self.value, list):
            raise ValueError("replace_reforge_procedure_steps requires list of step dicts")
        return self


class UnifiedProgram(BaseModel):
    schema_version: str = Field(default="2")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task: TaskAgentSpec = Field(default_factory=TaskAgentSpec)
    reforge_agent: ReforgeAgentSpec = Field(default_factory=ReforgeAgentSpec)
    reforge_procedure: ReforgeProcedureSpec = Field(default_factory=ReforgeProcedureSpec)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="before")
    @classmethod
    def _migrate_schema_v1(cls, data: Any) -> Any:
        """Accept legacy `meta` / `meta_procedure` keys (schema v1) for load_program compatibility."""
        if not isinstance(data, dict):
            return data
        d = dict(data)
        if "meta" in d and "reforge_agent" not in d:
            d["reforge_agent"] = d.pop("meta")
        if "meta_procedure" in d and "reforge_procedure" not in d:
            d["reforge_procedure"] = d.pop("meta_procedure")
        ra = d.get("reforge_agent")
        if isinstance(ra, dict) and "meta_procedure_patch_prompt" in ra:
            ra = dict(ra)
            ra["reforge_procedure_patch_prompt"] = ra.pop("meta_procedure_patch_prompt")
            d["reforge_agent"] = ra
        rp = d.get("reforge_procedure")
        if isinstance(rp, dict) and "steps" in rp:
            steps = rp["steps"]
            if isinstance(steps, list):
                new_steps = []
                for s in steps:
                    if isinstance(s, dict) and s.get("type") == "summarize_meta_memory":
                        s = dict(s)
                        s["type"] = "summarize_reforge_memory"
                    new_steps.append(s)
                rp = dict(rp)
                rp["steps"] = new_steps
                d["reforge_procedure"] = rp
        if d.get("schema_version") in (None, "1"):
            d["schema_version"] = "2"
        return d

    def content_fingerprint(self) -> str:
        payload = self.model_dump(mode="json", exclude={"id", "created_at", "updated_at"})
        raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


class Variant(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_program_id: str
    parent_fingerprint: str
    patches: list[ProgramPatchOp] = Field(default_factory=list)
    seed: int | None = None
    generator_id: str = "default"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvaluationReport(BaseModel):
    variant_id: str
    run_id: str
    metrics: dict[str, float] = Field(default_factory=dict)
    passed: bool = True
    stderr: str = ""
    artifact_uris: list[str] = Field(default_factory=list)
    failure_taxonomy: str | None = None
    raw_judge_output: dict[str, Any] | None = None
    evaluator_id: str = ""


class ArchiveEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    program: UnifiedProgram
    scores: dict[str, float] = Field(default_factory=dict)
    parent_entry_ids: list[str] = Field(default_factory=list)
    domain: DomainTag = DomainTag.GENERAL
    novelty_notes: str = ""
    embedding: list[float] | None = None
    reforge_memory_excerpt: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="before")
    @classmethod
    def _migrate_memory_field(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        if "meta_memory_excerpt" in d and "reforge_memory_excerpt" not in d:
            d["reforge_memory_excerpt"] = d.pop("meta_memory_excerpt")
        return d

    @property
    def fingerprint(self) -> str:
        return self.program.content_fingerprint()
