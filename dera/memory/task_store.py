from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from dera.paths import database_path as moon_database_path

from dera.tasks.task import Task


class TaskStore:
    """Small local audit log for Dera1.4 tasks."""

    def __init__(self, database_path: Path | None = None) -> None:
        self.database_path = database_path or moon_database_path()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, objective TEXT NOT NULL, state TEXT NOT NULL, payload TEXT NOT NULL)")
            connection.execute("CREATE TABLE IF NOT EXISTS task_events (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL, created_at TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL)")

    def save(self, task: Task) -> None:
        with self._connect() as connection:
            connection.execute("INSERT OR REPLACE INTO tasks (id, created_at, objective, state, payload) VALUES (?, ?, ?, ?, ?)", (task.id, task.created_at, task.objective, task.state, json.dumps(task.to_dict())))

    def get(self, task_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute("SELECT payload FROM tasks WHERE id = ?", (task_id,)).fetchone()
            events = connection.execute("SELECT created_at, kind, payload FROM task_events WHERE task_id = ? ORDER BY id", (task_id,)).fetchall()
        if not row:
            raise ValueError("Task was not found.")
        task = json.loads(row[0])
        task["activity"] = [{"created_at": event[0], "kind": event[1], "payload": json.loads(event[2])} for event in events]
        return task

    def list_recent(self, limit: int = 20) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute("SELECT id, created_at, objective, state FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [{"id": row[0], "created_at": row[1], "objective": row[2], "state": row[3]} for row in rows]

    def add_event(self, task_id: str, kind: str, payload: dict) -> None:
        from datetime import datetime, timezone
        self.get(task_id)
        with self._connect() as connection:
            connection.execute("INSERT INTO task_events (task_id, created_at, kind, payload) VALUES (?, ?, ?, ?)", (task_id, datetime.now(timezone.utc).isoformat(), kind, json.dumps(payload)))

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)
