"""Materialize TaskAgentSpec into user graph builder kwargs."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from layai_reforge.models.program import TaskAgentSpec


class GraphBuilder(Protocol):
    def __call__(self, spec: TaskAgentSpec, **kwargs: Any) -> Any: ...


def materialize_for_graph_builder(spec: TaskAgentSpec, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Default kwargs dict for a LangGraph-oriented builder."""
    base = {
        "system_prompt": spec.system_prompt,
        "tools": [t.model_dump() for t in spec.tools],
        "graph_config": dict(spec.graph_config),
        "model_hint": spec.model_hint,
        "max_steps": spec.max_steps,
        "tool_budget": spec.tool_budget,
    }
    if extra:
        base.update(extra)
    return base


def build_with_callable(builder: Callable[..., Any], spec: TaskAgentSpec, **kwargs: Any) -> Any:
    """Invoke user factory with materialized defaults merged with kwargs."""
    mat = materialize_for_graph_builder(spec)
    return builder(spec, **{**mat, **kwargs})
