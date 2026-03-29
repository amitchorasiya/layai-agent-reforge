from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from layai_reforge.models.program import ArchiveEntry, DomainTag, UnifiedProgram


class ArchiveStore(ABC):
    @abstractmethod
    def add_entry(self, entry: ArchiveEntry) -> str:
        """Persist entry; return entry id."""

    @abstractmethod
    def get_entry(self, entry_id: str) -> ArchiveEntry | None:
        pass

    @abstractmethod
    def list_entries(
        self,
        domain: DomainTag | None = None,
        limit: int = 100,
    ) -> list[ArchiveEntry]:
        pass

    @abstractmethod
    def retrieve_for_reforge_context(
        self,
        k: int = 5,
        domain: DomainTag | None = None,
        min_score_key: str | None = None,
    ) -> list[ArchiveEntry]:
        """Top-k by score with simple diversity (fingerprints)."""

    @abstractmethod
    def lineage(self, entry_id: str) -> list[ArchiveEntry]:
        """Ancestors ordered root-first (best-effort)."""

    def dedupe_fingerprint_exists(self, fingerprint: str) -> bool:
        entries = self.list_entries(limit=10_000)
        return any(e.fingerprint == fingerprint for e in entries)
