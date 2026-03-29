"""Redact common secret patterns from logs."""

from __future__ import annotations

import re

_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password|bearer)\s*[:=]\s*\S+"),
    re.compile(r"sk-[a-zA-Z0-9]{10,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
]


def redact_secrets(text: str) -> str:
    out = text
    for pat in _PATTERNS:
        out = pat.sub("[REDACTED]", out)
    return out
