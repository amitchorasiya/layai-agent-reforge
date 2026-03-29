"""Load/save UnifiedProgram as JSON or YAML."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from layai_reforge.models.program import UnifiedProgram


def load_program(path: Path | str) -> UnifiedProgram:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in {".yaml", ".yml"}:
        data: dict[str, Any] = yaml.safe_load(text)
    else:
        data = json.loads(text)
    return UnifiedProgram.model_validate(data)


def save_program(program: UnifiedProgram, path: Path | str, format: str | None = None) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fmt = format or ("yaml" if p.suffix.lower() in {".yaml", ".yml"} else "json")
    if fmt == "yaml":
        body = yaml.safe_dump(program.model_dump(mode="json"), sort_keys=False, allow_unicode=True)
    else:
        body = json.dumps(program.model_dump(mode="json"), indent=2, default=str)
    p.write_text(body, encoding="utf-8")
