"""Structured logging and optional OpenTelemetry hooks."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Generator

logger = logging.getLogger("layai_reforge")


def log_event(event: str, **fields: Any) -> None:
    logger.info("%s %s", event, fields)


@contextmanager
def span(name: str, **attrs: Any) -> Generator[None, None, None]:
    try:
        from opentelemetry import trace  # type: ignore

        tracer = trace.get_tracer("layai_reforge")
        with tracer.start_as_current_span(name, attributes=attrs):
            yield
    except Exception:
        yield
