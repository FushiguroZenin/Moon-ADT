from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from dera.paths import database_path as moon_database_path


class MonitorStore:
    def __init__(self, database_path: Path | None = None) -> None:
        self.database_path = database_path or moon_database_path()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS monitor_snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, payload TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS monitor_events (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, payload TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS monitor_settings (id INTEGER PRIMARY KEY CHECK (id = 1), enabled INTEGER NOT NULL, interval_minutes INTEGER NOT NULL, last_checked_at TEXT)")
            db.execute("INSERT OR IGNORE INTO monitor_settings (id, enabled, interval_minutes, last_checked_at) VALUES (1, 0, 30, NULL)")

    def latest(self) -> dict | None:
        with sqlite3.connect(self.database_path) as db:
            row = db.execute("SELECT payload FROM monitor_snapshots ORDER BY id DESC LIMIT 1").fetchone()
        return json.loads(row[0]) if row else None

    def save(self, snapshot: dict) -> None:
        with sqlite3.connect(self.database_path) as db:
            db.execute("INSERT INTO monitor_snapshots (created_at, payload) VALUES (?, ?)", (snapshot["observed_at"], json.dumps(snapshot)))

    def list_recent(self, limit: int = 10) -> list[dict]:
        with sqlite3.connect(self.database_path) as db:
            rows = db.execute("SELECT payload FROM monitor_snapshots ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def settings(self) -> dict:
        with sqlite3.connect(self.database_path) as db:
            row = db.execute("SELECT enabled, interval_minutes, last_checked_at FROM monitor_settings WHERE id = 1").fetchone()
        return {"enabled": bool(row[0]), "interval_minutes": row[1], "last_checked_at": row[2]}

    def update_settings(self, enabled: bool, interval_minutes: int) -> dict:
        with sqlite3.connect(self.database_path) as db:
            db.execute("UPDATE monitor_settings SET enabled = ?, interval_minutes = ? WHERE id = 1", (int(enabled), interval_minutes))
        return self.settings()

    def record_check(self, findings: list[dict], observed_at: str) -> None:
        with sqlite3.connect(self.database_path) as db:
            db.execute("UPDATE monitor_settings SET last_checked_at = ? WHERE id = 1", (observed_at,))
            if findings:
                db.execute("INSERT INTO monitor_events (created_at, payload) VALUES (?, ?)", (observed_at, json.dumps({"findings": findings})))

    def list_events(self, limit: int = 20) -> list[dict]:
        with sqlite3.connect(self.database_path) as db:
            rows = db.execute("SELECT created_at, payload FROM monitor_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{"created_at": row[0], **json.loads(row[1])} for row in rows]
