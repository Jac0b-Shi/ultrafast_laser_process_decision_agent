from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from app.schemas import ExperimentFeedback, FeedbackReceipt
from app.settings import get_settings


def _ensure_sqlite() -> None:
    settings = get_settings()
    settings.experiments_dir.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(settings.sqlite_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.commit()


def append_feedback(feedback: ExperimentFeedback) -> FeedbackReceipt:
    settings = get_settings()
    settings.feedback_dir.mkdir(parents=True, exist_ok=True)
    _ensure_sqlite()

    feedback_id = str(uuid4())
    created_at = datetime.now(timezone.utc)
    payload = feedback.model_dump(mode="json")
    payload["feedback_id"] = feedback_id
    payload["created_at"] = created_at.isoformat()
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)

    with settings.feedback_jsonl.open("a", encoding="utf-8") as handle:
        handle.write(payload_json + "\n")

    with sqlite3.connect(settings.sqlite_path) as conn:
        conn.execute(
            "INSERT INTO feedback (feedback_id, created_at, payload_json) VALUES (?, ?, ?)",
            (feedback_id, created_at.isoformat(), payload_json),
        )
        conn.commit()

    return FeedbackReceipt(
        feedback_id=feedback_id,
        created_at=created_at,
        stored_jsonl=str(settings.feedback_jsonl),
        stored_sqlite=str(settings.sqlite_path),
    )
