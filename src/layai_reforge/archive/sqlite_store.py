"""SQLite-backed stepping-stone archive."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from layai_reforge.archive.base import ArchiveStore
from layai_reforge.models.program import ArchiveEntry, DomainTag, UnifiedProgram


class SqliteArchiveStore(ArchiveStore):
    def __init__(self, db_path: Path | str) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS archive_entries (
                id TEXT PRIMARY KEY,
                fingerprint TEXT NOT NULL,
                domain TEXT NOT NULL,
                entry_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_archive_fp ON archive_entries(fingerprint);
            CREATE INDEX IF NOT EXISTS idx_archive_domain ON archive_entries(domain);
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def add_entry(self, entry: ArchiveEntry) -> str:
        fp = entry.fingerprint
        cur = self._conn.execute(
            "SELECT id FROM archive_entries WHERE fingerprint = ?",
            (fp,),
        )
        existing = cur.fetchone()
        if existing:
            return str(existing[0])

        payload = json.dumps(entry.model_dump(mode="json"), default=str)
        self._conn.execute(
            "INSERT INTO archive_entries (id, fingerprint, domain, entry_json, created_at) VALUES (?,?,?,?,?)",
            (
                entry.id,
                fp,
                entry.domain.value,
                payload,
                entry.created_at.isoformat(),
            ),
        )
        self._conn.commit()
        return entry.id

    def get_entry(self, entry_id: str) -> ArchiveEntry | None:
        cur = self._conn.execute(
            "SELECT entry_json FROM archive_entries WHERE id = ?",
            (entry_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return ArchiveEntry.model_validate(json.loads(row["entry_json"]))

    def list_entries(
        self,
        domain: DomainTag | None = None,
        limit: int = 100,
    ) -> list[ArchiveEntry]:
        if domain:
            cur = self._conn.execute(
                "SELECT entry_json FROM archive_entries WHERE domain = ? ORDER BY created_at DESC LIMIT ?",
                (domain.value, limit),
            )
        else:
            cur = self._conn.execute(
                "SELECT entry_json FROM archive_entries ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        return [ArchiveEntry.model_validate(json.loads(r["entry_json"])) for r in cur.fetchall()]

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
            fp = e.fingerprint
            if fp in seen_fp:
                continue
            seen_fp.add(fp)
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
            parent_id = current.parent_entry_ids[0]
            current = self.get_entry(parent_id)
        chain.reverse()
        return chain

    def dedupe_fingerprint_exists(self, fingerprint: str) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM archive_entries WHERE fingerprint = ? LIMIT 1",
            (fingerprint,),
        )
        return cur.fetchone() is not None
