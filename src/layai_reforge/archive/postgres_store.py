"""Postgres archive backend (optional extra: psycopg)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from layai_reforge.archive.base import ArchiveStore
from layai_reforge.models.program import ArchiveEntry, DomainTag

try:
    import psycopg
except ImportError:
    psycopg = None  # type: ignore[misc, assignment]


class PostgresArchiveStore(ArchiveStore):
    def __init__(self, conninfo: str) -> None:
        if psycopg is None:
            raise RuntimeError("Install layai-agent-reforge[postgres] for PostgresArchiveStore")
        self._conninfo = conninfo
        self._ensure_schema()

    def _connect(self):
        return psycopg.connect(self._conninfo)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reforge_archive_entries (
                    id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    entry_json JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_reforge_fp ON reforge_archive_entries(fingerprint);
                CREATE INDEX IF NOT EXISTS idx_reforge_domain ON reforge_archive_entries(domain);
                """
            )

    def add_entry(self, entry: ArchiveEntry) -> str:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT id FROM reforge_archive_entries WHERE fingerprint = %s",
                (entry.fingerprint,),
            )
            row = cur.fetchone()
            if row:
                return row[0]
            payload = json.dumps(entry.model_dump(mode="json"), default=str)
            conn.execute(
                """INSERT INTO reforge_archive_entries (id, fingerprint, domain, entry_json, created_at)
                   VALUES (%s,%s,%s,%s::jsonb,%s)""",
                (
                    entry.id,
                    entry.fingerprint,
                    entry.domain.value,
                    payload,
                    entry.created_at.isoformat(),
                ),
            )
            conn.commit()
        return entry.id

    def get_entry(self, entry_id: str) -> ArchiveEntry | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT entry_json FROM reforge_archive_entries WHERE id = %s",
                (entry_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return ArchiveEntry.model_validate(row[0] if isinstance(row[0], dict) else json.loads(row[0]))

    def list_entries(
        self,
        domain: DomainTag | None = None,
        limit: int = 100,
    ) -> list[ArchiveEntry]:
        with self._connect() as conn:
            if domain:
                cur = conn.execute(
                    "SELECT entry_json FROM reforge_archive_entries WHERE domain = %s ORDER BY created_at DESC LIMIT %s",
                    (domain.value, limit),
                )
            else:
                cur = conn.execute(
                    "SELECT entry_json FROM reforge_archive_entries ORDER BY created_at DESC LIMIT %s",
                    (limit,),
                )
            rows = cur.fetchall()
        out: list[ArchiveEntry] = []
        for r in rows:
            j = r[0]
            out.append(ArchiveEntry.model_validate(j if isinstance(j, dict) else json.loads(j)))
        return out

    def retrieve_for_reforge_context(
        self,
        k: int = 5,
        domain: DomainTag | None = None,
        min_score_key: str | None = None,
    ) -> list[ArchiveEntry]:
        entries = self.list_entries(domain=domain, limit=min(500, max(k * 20, k)))

        def sort_key(e: ArchiveEntry) -> float:
            if min_score_key and min_score_key in e.scores:
                return float(e.scores[min_score_key])
            if e.scores:
                return max(e.scores.values())
            return 0.0

        entries.sort(key=sort_key, reverse=True)
        seen_fp: set[str] = set()
        out: list[ArchiveEntry] = []
        for e in entries:
            if e.fingerprint in seen_fp:
                continue
            seen_fp.add(e.fingerprint)
            out.append(e)
            if len(out) >= k:
                break
        return out

    def lineage(self, entry_id: str) -> list[ArchiveEntry]:
        chain: list[ArchiveEntry] = []
        current = self.get_entry(entry_id)
        visited: set[str] = set()
        while current and current.id not in visited:
            visited.add(current.id)
            chain.append(current)
            if not current.parent_entry_ids:
                break
            current = self.get_entry(current.parent_entry_ids[0])
        chain.reverse()
        return chain

    def dedupe_fingerprint_exists(self, fingerprint: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT 1 FROM reforge_archive_entries WHERE fingerprint = %s LIMIT 1",
                (fingerprint,),
            )
            return cur.fetchone() is not None
