from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from layai_reforge.models.program import EvaluationReport, Variant


class PromotionAuditRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    variant_id: str
    approved: bool
    actor: str = "system"
    patches_json: str = ""
    report_metrics_json: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLogStore:
    def __init__(self, db_path: Path | str) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS promotion_audit (
                id TEXT PRIMARY KEY,
                variant_id TEXT NOT NULL,
                approved INTEGER NOT NULL,
                actor TEXT NOT NULL,
                patches_json TEXT NOT NULL,
                report_metrics_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def record_promotion(
        self,
        variant: Variant,
        report: EvaluationReport,
        approved: bool,
        actor: str = "human",
    ) -> str:
        rec = PromotionAuditRecord(
            variant_id=variant.id,
            approved=approved,
            actor=actor,
            patches_json=json.dumps([p.model_dump() for p in variant.patches], default=str),
            report_metrics_json=json.dumps(report.metrics, default=str),
        )
        self._conn.execute(
            "INSERT INTO promotion_audit (id, variant_id, approved, actor, patches_json, report_metrics_json, created_at) VALUES (?,?,?,?,?,?,?)",
            (
                rec.id,
                rec.variant_id,
                1 if rec.approved else 0,
                rec.actor,
                rec.patches_json,
                rec.report_metrics_json,
                rec.created_at.isoformat(),
            ),
        )
        self._conn.commit()
        return rec.id

    def close(self) -> None:
        self._conn.close()
