"""Cross-domain transfer hooks for archive context."""

from __future__ import annotations

from layai_reforge.archive.base import ArchiveStore
from layai_reforge.models.program import ArchiveEntry, DomainTag


class TransferPolicy:
    def __init__(self, allow_cross_domain: bool = True) -> None:
        self.allow_cross_domain = allow_cross_domain

    def pull_for_domain(
        self,
        store: ArchiveStore,
        target_domain: DomainTag,
        source_domains: list[DomainTag] | None = None,
        k: int = 3,
    ) -> list[ArchiveEntry]:
        if not self.allow_cross_domain:
            return store.retrieve_for_reforge_context(k=k, domain=target_domain)
        sources = source_domains or list(DomainTag)
        out: list[ArchiveEntry] = []
        for d in sources:
            if d == target_domain:
                continue
            out.extend(store.retrieve_for_reforge_context(k=k, domain=d))
        return out[: k * len(sources)]
