from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dera.paths import database_path as moon_database_path


class PairingService:
    """Local pairing state. No remote transport is created by this service."""

    def __init__(self, database_path: Path | None = None) -> None:
        self.database_path = database_path or moon_database_path()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS device_identity (id INTEGER PRIMARY KEY CHECK (id = 1), device_id TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS pairing_codes (code_hash TEXT PRIMARY KEY, expires_at TEXT NOT NULL, used INTEGER NOT NULL DEFAULT 0)")
            db.execute("CREATE TABLE IF NOT EXISTS paired_clients (token_hash TEXT PRIMARY KEY, client_name TEXT NOT NULL, paired_at TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS pairing_audit (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, event TEXT NOT NULL, detail TEXT NOT NULL)")

    def active_code_records(self) -> list[dict]:
        """Return hashes only for an outbound relay pairing exchange."""
        now = datetime.now(timezone.utc)
        with sqlite3.connect(self.database_path) as db:
            rows = db.execute("SELECT code_hash, expires_at FROM pairing_codes WHERE used = 0").fetchall()
        return [
            {"code_hash": row[0], "expires_at": row[1]}
            for row in rows
            if datetime.fromisoformat(row[1]) > now
        ]

    def status(self) -> dict:
        with sqlite3.connect(self.database_path) as db:
            device = db.execute("SELECT device_id FROM device_identity WHERE id = 1").fetchone()
            clients = db.execute("SELECT client_name, paired_at FROM paired_clients ORDER BY paired_at DESC").fetchall()
        return {"device_id": device[0] if device else None, "paired_clients": [{"name": row[0], "paired_at": row[1]} for row in clients], "remote_access": "not configured"}

    def create_code(self) -> dict:
        device_id = self._device_id()
        code = "-".join([secrets.token_hex(2).upper() for _ in range(3)])
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        with sqlite3.connect(self.database_path) as db:
            db.execute("INSERT INTO pairing_codes (code_hash, expires_at) VALUES (?, ?)", (self._hash(code), expires_at.isoformat()))
            self._audit(db, "pairing_code_created", device_id)
        return {"device_id": device_id, "code": code, "expires_at": expires_at.isoformat()}

    def complete(self, code: str, client_name: str) -> dict:
        now = datetime.now(timezone.utc)
        with sqlite3.connect(self.database_path) as db:
            row = db.execute("SELECT expires_at, used FROM pairing_codes WHERE code_hash = ?", (self._hash(code),)).fetchone()
            if not row or row[1] or datetime.fromisoformat(row[0]) <= now:
                raise ValueError("The pairing code is invalid, used, or expired.")
            token = secrets.token_urlsafe(32)
            db.execute("UPDATE pairing_codes SET used = 1 WHERE code_hash = ?", (self._hash(code),))
            db.execute("INSERT INTO paired_clients (token_hash, client_name, paired_at) VALUES (?, ?, ?)", (self._hash(token), client_name[:80], now.isoformat()))
            self._audit(db, "client_paired", client_name[:80])
        return {"device_id": self._device_id(), "token": token, "client_name": client_name}

    def _device_id(self) -> str:
        with sqlite3.connect(self.database_path) as db:
            row = db.execute("SELECT device_id FROM device_identity WHERE id = 1").fetchone()
            if row:
                return row[0]
            value = "moon_" + secrets.token_urlsafe(12)
            db.execute("INSERT INTO device_identity (id, device_id) VALUES (1, ?)", (value,))
            return value

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    @staticmethod
    def _audit(db: sqlite3.Connection, event: str, detail: str) -> None:
        db.execute("INSERT INTO pairing_audit (created_at, event, detail) VALUES (?, ?, ?)", (datetime.now(timezone.utc).isoformat(), event, detail))
