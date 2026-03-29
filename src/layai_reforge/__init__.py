"""Layerd AI Agent Reforge — outer-loop self-improvement for agents (HyperAgents-inspired)."""

from layai_reforge.archive import MergePolicy, SqliteArchiveStore, merge_archives
from layai_reforge.models import (
    ArchiveEntry,
    DomainTag,
    EvaluationReport,
    ProgramPatchOp,
    ReforgeAgentSpec,
    ReforgeProcedureSpec,
    ReforgeProcedureStep,
    RunArtifact,
    TaskAgentSpec,
    ToolDescriptor,
    UnifiedProgram,
    Variant,
)
from layai_reforge.program_io import load_program, save_program
from layai_reforge.session import ReforgeSession

__all__ = [
    "ArchiveEntry",
    "DomainTag",
    "EvaluationReport",
    "MergePolicy",
    "ProgramPatchOp",
    "ReforgeAgentSpec",
    "ReforgeProcedureSpec",
    "ReforgeProcedureStep",
    "ReforgeSession",
    "RunArtifact",
    "SqliteArchiveStore",
    "TaskAgentSpec",
    "ToolDescriptor",
    "UnifiedProgram",
    "Variant",
    "load_program",
    "merge_archives",
    "save_program",
]

__version__ = "0.2.1"
