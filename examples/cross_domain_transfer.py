"""Demonstrate TransferPolicy pulling archive context across DomainTag buckets."""

from __future__ import annotations

import tempfile
from pathlib import Path

from layai_reforge import ArchiveEntry, DomainTag, SqliteArchiveStore, UnifiedProgram
from layai_reforge.models.program import TaskAgentSpec
from layai_reforge.transfer import TransferPolicy


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = SqliteArchiveStore(Path(td) / "x.sqlite")
        p = UnifiedProgram(task=TaskAgentSpec(system_prompt="coding helper"))
        store.add_entry(
            ArchiveEntry(program=p, scores={"score": 0.9}, domain=DomainTag.CODING)
        )
        policy = TransferPolicy(allow_cross_domain=True)
        pulled = policy.pull_for_domain(store, target_domain=DomainTag.MATH, k=2)
        print("cross_domain_entries", len(pulled))


if __name__ == "__main__":
    main()
