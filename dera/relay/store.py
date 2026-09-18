from __future__ import annotations

import secrets
import sqlite3
from pathlib import Path
from dera.paths import database_path as moon_database_path


class RelayStore:
    """Persists local relay configuration; secrets never leave this store directly."""

    def __init__(self, database_path: Path | None = None) -> None:
        self.database_path = database_path or moon_database_path()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS relay_settings (id INTEGER PRIMARY KEY CHECK (id = 1), relay_url TEXT, enabled INTEGER NOT NULL, signing_secret TEXT NOT NULL)")
            columns = {row[1] for row in db.execute("PRAGMA table_info(relay_settings)")}
            if "device_token" not in columns:
                db.execute("ALTER TABLE relay_settings ADD COLUMN device_token TEXT")
            db.execute("INSERT OR IGNORE INTO relay_settings (id, relay_url, enabled, signing_secret) VALUES (1, NULL, 0, ?)", (secrets.token_urlsafe(48),))

    def get(self) -> dict:
        with sqlite3.connect(self.database_path) as db:
            row = db.execute("SELECT relay_url, enabled FROM relay_settings WHERE id = 1").fetchone()
        return {"relay_url": row[0], "enabled": bool(row[1]), "mode": "outbound only"}

    def secret(self) -> str:
        with sqlite3.connect(self.database_path) as db:
            return db.execute("SELECT signing_secret FROM relay_settings WHERE id = 1").fetchone()[0]

    def configure(self, relay_url: str | None, enabled: bool) -> dict:
        with sqlite3.connect(self.database_path) as db:
            db.execute("UPDATE relay_settings SET relay_url = ?, enabled = ? WHERE id = 1", (relay_url, int(enabled)))
        return self.get()

    def token(self) -> str | None:
        with sqlite3.connect(self.database_path) as db:
            return db.execute("SELECT device_token FROM relay_settings WHERE id = 1").fetchone()[0]

    def save_token(self, token: str) -> None:
        with sqlite3.connect(self.database_path) as db:
            db.execute("UPDATE relay_settings SET device_token = ? WHERE id = 1", (token,))
