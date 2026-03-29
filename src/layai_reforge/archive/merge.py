"""Export/import and merge archive bundles."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Iterable

from layai_reforge.archive.base import ArchiveStore
from layai_reforge.models.program import ArchiveEntry


class MergePolicy(str, Enum):
    UNION = "union"
    PARETO_FRONTIER = "pareto_frontier"
    NOVELTY_ONLY = "novelty_only"


def export_archive_json(store: ArchiveStore, limit: int = 10_000) -> str:
    entries = store.list_entries(limit=limit)
    return json.dumps([e.model_dump(mode="json") for e in entries], indent=2, default=str)


def import_archive_entries(data: str | list) -> list[ArchiveEntry]:
    raw = json.loads(data) if isinstance(data, str) else data
    return [ArchiveEntry.model_validate(x) for x in raw]


def merge_archives(
    target: ArchiveStore,
    incoming: Iterable[ArchiveEntry],
    policy: MergePolicy = MergePolicy.UNION,
    score_key: str = "aggregate",
) -> int:
    """Insert incoming entries; return count added (skips duplicate fingerprint)."""
    added = 0
    incoming_list = list(incoming)
    if policy == MergePolicy.PARETO_FRONTIER and incoming_list:
        incoming_list = _pareto_filter(incoming_list, score_key)
    for e in incoming_list:
        if target.dedupe_fingerprint_exists(e.fingerprint):
            continue
        target.add_entry(e)
        added += 1
    return added


def _pareto_filter(entries: list[ArchiveEntry], score_key: str) -> list[ArchiveEntry]:
    """Keep entries not dominated on all score keys present (simple 1-key case)."""
    if not entries:
        return []
    if score_key:
        best = max((e.scores.get(score_key, 0.0) for e in entries), default=0.0)
        return [e for e in entries if e.scores.get(score_key, 0.0) >= best - 1e-9]
    return entries


def write_bundle(path: Path, store: ArchiveStore, limit: int = 10_000) -> None:
    path.write_text(export_archive_json(store, limit=limit), encoding="utf-8")


def read_bundle(path: Path) -> list[ArchiveEntry]:
    return import_archive_entries(path.read_text(encoding="utf-8"))
