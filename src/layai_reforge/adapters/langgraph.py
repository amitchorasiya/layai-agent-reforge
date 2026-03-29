"""Optional LangGraph helpers: capture RunArtifact from graph runs."""

from __future__ import annotations

import uuid
from typing import Any

from layai_reforge.models.artifacts import RunArtifact


def run_artifact_from_langgraph_result(
    result: dict[str, Any] | Any,
    *,
    variant_id: str | None = None,
    program_fingerprint: str = "",
) -> RunArtifact:
    """Best-effort extraction from LangGraph invoke() output dict."""
    run_id = str(uuid.uuid4())
    messages: list[dict[str, Any]] = []
    tool_calls: list[dict[str, Any]] = []

    if isinstance(result, dict):
        msgs = result.get("messages") or []
        for m in msgs:
            if hasattr(m, "model_dump"):
                messages.append(m.model_dump())
            elif isinstance(m, dict):
                messages.append(m)
            else:
                messages.append({"type": type(m).__name__, "content": str(m)})
            tc = getattr(m, "tool_calls", None) or (m.get("tool_calls") if isinstance(m, dict) else None)
            if tc:
                for t in tc:
                    if hasattr(t, "model_dump"):
                        tool_calls.append(t.model_dump())
                    elif isinstance(t, dict):
                        tool_calls.append(t)
    return RunArtifact(
        run_id=run_id,
        variant_id=variant_id,
        program_fingerprint=program_fingerprint,
        messages=messages,
        tool_calls=tool_calls,
        success=True,
    )


def wrap_invoke(graph: Any, input_state: dict[str, Any], **kwargs: Any) -> RunArtifact:
    """Invoke compiled graph and return RunArtifact."""
    out = graph.invoke(input_state, **kwargs)
    return run_artifact_from_langgraph_result(out, **kwargs)
