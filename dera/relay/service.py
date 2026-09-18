"""Moon relay service foundation.

Run separately from a Dera1.4 runtime. The relay stores device events and queues
read-only requests; it never performs a computer action itself.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


class DeviceRegistration(BaseModel):
    device_id: str


class QueuedCommand(BaseModel):
    command_type: str
    payload: dict = {}


class PairingCodeSync(BaseModel):
    codes: list[dict] = []


class BrowserPairing(BaseModel):
    code: str
    client_name: str = "Moon web"


class BrowserQuestion(BaseModel):
    request: str


class RelayDatabase:
    def __init__(self) -> None:
        self.path = Path(os.getenv("MOON_RELAY_DATABASE", "data/moon-relay.db"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS devices (device_id TEXT PRIMARY KEY, token_hash TEXT NOT NULL, registered_at TEXT NOT NULL, last_seen_at TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS device_events (id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS commands (id TEXT PRIMARY KEY, device_id TEXT NOT NULL, created_at TEXT NOT NULL, command_type TEXT NOT NULL, payload TEXT NOT NULL, delivered INTEGER NOT NULL DEFAULT 0)")
            db.execute("CREATE TABLE IF NOT EXISTS browser_pairing_codes (code_hash TEXT PRIMARY KEY, device_id TEXT NOT NULL, expires_at TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS browser_sessions (session_hash TEXT PRIMARY KEY, device_id TEXT NOT NULL, client_name TEXT NOT NULL, created_at TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS command_results (command_id TEXT PRIMARY KEY, completed_at TEXT NOT NULL, result TEXT NOT NULL)")
            columns = {row[1] for row in db.execute("PRAGMA table_info(commands)")}
            if "browser_session_hash" not in columns:
                db.execute("ALTER TABLE commands ADD COLUMN browser_session_hash TEXT")

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)


database = RelayDatabase()
app = FastAPI(title="Moon outbound relay", version="0.1.0", docs_url="/docs")
web_origins = [origin.strip() for origin in os.getenv("MOON_WEB_ORIGIN", "").split(",") if origin.strip()]
if web_origins:
    app.add_middleware(CORSMiddleware, allow_origins=web_origins, allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def require_device(request: Request, device_id: str) -> None:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Device bearer token is required.")
    with database.connect() as db:
        row = db.execute("SELECT token_hash FROM devices WHERE device_id = ?", (device_id,)).fetchone()
    if not row or not secrets.compare_digest(row[0], token_hash(header[7:])):
        raise HTTPException(status_code=401, detail="Device authentication failed.")


def _session_secret() -> bytes:
    """Return the relay-owned key used to validate stateless browser sessions."""
    secret = os.getenv("MOON_RELAY_SESSION_SECRET", "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="Moon relay session signing is not configured.")
    return secret.encode()


def _urlsafe_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _urlsafe_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue_browser_session(device_id: str, client_name: str) -> str:
    """Create a signed session that survives relay-instance restarts."""
    payload = json.dumps({"device_id": device_id, "client_name": client_name[:80], "issued_at": now()}, separators=(",", ":")).encode()
    encoded = _urlsafe_encode(payload)
    signature = hmac.new(_session_secret(), encoded.encode(), hashlib.sha256).digest()
    return f"{encoded}.{_urlsafe_encode(signature)}"


def stateless_browser_session(token: str) -> str | None:
    """Validate a signed browser session and return its paired device ID."""
    try:
        encoded, supplied_signature = token.split(".", 1)
        expected_signature = hmac.new(_session_secret(), encoded.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected_signature, _urlsafe_decode(supplied_signature)):
            return None
        payload = json.loads(_urlsafe_decode(encoded))
        device_id = payload.get("device_id")
        return device_id if isinstance(device_id, str) and device_id.startswith("moon_") else None
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def browser_session(request: Request) -> tuple[str, str]:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Browser pairing session is required.")
    token = header[7:]
    session_hash = token_hash(token)
    device_id = stateless_browser_session(token)
    if device_id:
        return session_hash, device_id
    with database.connect() as db:
        row = db.execute("SELECT device_id FROM browser_sessions WHERE session_hash = ?", (session_hash,)).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Browser pairing session is invalid or revoked.")
    return session_hash, row[0]


def browser_intent(request: str) -> str:
    """Conservative relay-side mapping; it cannot select arbitrary tools."""
    text = request.lower()
    if any(term in text for term in ("startup", "start up", "boot", "slow boot", "takes forever to start")):
        return "diagnose_startup_applications"
    if any(term in text for term in ("crash", "crashing", "keeps closing", "closed unexpectedly", "stopped working")):
        return "investigate_application_crash"
    if any(term in text for term in ("slow", "sluggish", "lag", "laggy", "stutter", "freez", "unresponsive", "performance", "hanging")):
        return "investigate_slow_computer"
    if any(term in text for term in ("downloads", "download folder", "downloaded files", "large files")):
        return "inspect_downloads"
    if any(term in text for term in ("system status", "computer status", "memory", "ram", "cpu", "processor", "battery", "network", "disk space", "storage")):
        return "system_status"
    return "unknown"


@app.get("/")
def health() -> dict:
    return {"service": "Moon outbound relay", "status": "running", "authority": "no computer-control authority"}


@app.post("/v1/devices/register")
def register_device(body: DeviceRegistration) -> dict:
    """Development device enrollment. Browser pairing remains device-first."""
    if not body.device_id.startswith("moon_") or len(body.device_id) > 120:
        raise HTTPException(status_code=400, detail="Invalid device ID.")
    token = secrets.token_urlsafe(32)
    with database.connect() as db:
        existing = db.execute("SELECT device_id FROM devices WHERE device_id = ?", (body.device_id,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="This Moon device is already enrolled. Existing device credentials cannot be replaced remotely.")
        db.execute("INSERT INTO devices (device_id, token_hash, registered_at, last_seen_at) VALUES (?, ?, ?, NULL)", (body.device_id, token_hash(token), now()))
    return {"device_id": body.device_id, "device_token": token}


@app.post("/v1/devices/{device_id}/pairing-codes")
def sync_pairing_codes(device_id: str, body: PairingCodeSync, request: Request) -> dict:
    """Accept hashes only; raw pairing codes stay with the user and local runtime."""
    require_device(request, device_id)
    valid = []
    for item in body.codes[:10]:
        code_hash, expires_at = item.get("code_hash"), item.get("expires_at")
        if isinstance(code_hash, str) and len(code_hash) == 64 and isinstance(expires_at, str):
            valid.append((code_hash, device_id, expires_at))
    with database.connect() as db:
        db.execute("DELETE FROM browser_pairing_codes WHERE device_id = ?", (device_id,))
        db.executemany("INSERT INTO browser_pairing_codes (code_hash, device_id, expires_at) VALUES (?, ?, ?)", valid)
    return {"published": len(valid)}


@app.post("/v1/browser-pairing/complete")
def complete_browser_pairing(body: BrowserPairing) -> dict:
    """Exchange a one-time PC-generated code for an opaque browser session."""
    hashed = token_hash(body.code.strip().upper())
    with database.connect() as db:
        row = db.execute("SELECT device_id, expires_at FROM browser_pairing_codes WHERE code_hash = ?", (hashed,)).fetchone()
        if not row or datetime.fromisoformat(row[1]) <= datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="The pairing code is invalid, expired, or has not reached the relay yet.")
        session = issue_browser_session(row[0], body.client_name)
        db.execute("DELETE FROM browser_pairing_codes WHERE code_hash = ?", (hashed,))
        db.execute("INSERT INTO browser_sessions (session_hash, device_id, client_name, created_at) VALUES (?, ?, ?, ?)", (token_hash(session), row[0], body.client_name[:80], now()))
    return {"device_id": row[0], "browser_session": session, "client_name": body.client_name[:80]}


@app.get("/v1/browser-pairing/session")
def browser_pairing_session(request: Request) -> dict:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Browser pairing session is required.")
    with database.connect() as db:
        row = db.execute("SELECT device_id, client_name, created_at FROM browser_sessions WHERE session_hash = ?", (token_hash(header[7:]),)).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Browser pairing session is invalid or revoked.")
    return {"device_id": row[0], "client_name": row[1], "paired_at": row[2]}


@app.get("/v1/devices/{device_id}/browser-sessions")
def list_browser_sessions(device_id: str, request: Request) -> dict:
    require_device(request, device_id)
    with database.connect() as db:
        rows = db.execute("SELECT rowid, client_name, created_at FROM browser_sessions WHERE device_id = ? ORDER BY created_at DESC", (device_id,)).fetchall()
    return {"clients": [{"id": str(row[0]), "name": row[1], "paired_at": row[2]} for row in rows]}


@app.delete("/v1/devices/{device_id}/browser-sessions/{client_id}")
def revoke_browser_session(device_id: str, client_id: int, request: Request) -> dict:
    require_device(request, device_id)
    with database.connect() as db:
        deleted = db.execute("DELETE FROM browser_sessions WHERE rowid = ? AND device_id = ?", (client_id, device_id)).rowcount
    if not deleted:
        raise HTTPException(status_code=404, detail="Paired browser was not found.")
    return {"revoked": True, "client_id": str(client_id)}


@app.post("/v1/devices/{device_id}/events")
async def receive_event(device_id: str, request: Request) -> dict:
    require_device(request, device_id)
    payload = await request.json()
    with database.connect() as db:
        db.execute("INSERT INTO device_events (device_id, created_at, payload) VALUES (?, ?, ?)", (device_id, now(), json.dumps(payload)))
        if payload.get("message_type") == "command.result":
            command_id = str((payload.get("payload") or {}).get("command_id", ""))
            result = (payload.get("payload") or {}).get("result")
            owned = db.execute("SELECT id FROM commands WHERE id = ? AND device_id = ?", (command_id, device_id)).fetchone()
            if owned and isinstance(result, dict):
                db.execute("INSERT OR REPLACE INTO command_results (command_id, completed_at, result) VALUES (?, ?, ?)", (command_id, now(), json.dumps(result)))
        db.execute("UPDATE devices SET last_seen_at = ? WHERE device_id = ?", (now(), device_id))
    return {"accepted": True}


@app.get("/v1/devices/{device_id}/commands")
def poll_commands(device_id: str, request: Request) -> dict:
    require_device(request, device_id)
    with database.connect() as db:
        rows = db.execute("SELECT id, command_type, payload FROM commands WHERE device_id = ? AND delivered = 0 ORDER BY created_at", (device_id,)).fetchall()
        db.executemany("UPDATE commands SET delivered = 1 WHERE id = ?", [(row[0],) for row in rows])
    return {"commands": [{"id": row[0], "command_type": row[1], "payload": json.loads(row[2])} for row in rows]}


@app.post("/v1/devices/{device_id}/commands")
def enqueue_read_only_command(device_id: str, body: QueuedCommand, request: Request) -> dict:
    admin_key = os.getenv("MOON_RELAY_ADMIN_KEY")
    if not admin_key or not secrets.compare_digest(request.headers.get("X-Relay-Admin-Key", ""), admin_key):
        raise HTTPException(status_code=403, detail="Relay administration authentication is required.")
    allowed = {"system_status", "investigate_slow_computer", "inspect_downloads", "diagnose_startup_applications", "investigate_application_crash"}
    if body.command_type not in allowed:
        raise HTTPException(status_code=400, detail="Only read-only Dera1.4 requests may be queued by the relay.")
    command_id = secrets.token_urlsafe(16)
    with database.connect() as db:
        db.execute("INSERT INTO commands (id, device_id, created_at, command_type, payload) VALUES (?, ?, ?, ?, ?)", (command_id, device_id, now(), body.command_type, json.dumps(body.payload)))
    return {"command_id": command_id, "state": "queued", "execution": "not performed by relay"}


@app.post("/v1/browser/commands")
def browser_read_only_command(body: QueuedCommand, request: Request) -> dict:
    """Queue a scoped browser request; no action-changing command is accepted."""
    session_hash, device_id = browser_session(request)
    allowed = {"system_status", "investigate_slow_computer", "inspect_downloads", "diagnose_startup_applications", "investigate_application_crash"}
    if body.command_type not in allowed:
        raise HTTPException(status_code=400, detail="Paired browsers may request only Dera1.4 read-only investigations.")
    command_id = secrets.token_urlsafe(16)
    with database.connect() as db:
        db.execute("INSERT INTO commands (id, device_id, created_at, command_type, payload, browser_session_hash) VALUES (?, ?, ?, ?, ?, ?)", (command_id, device_id, now(), body.command_type, json.dumps(body.payload), session_hash))
    return {"command_id": command_id, "state": "queued", "scope": "read-only"}


@app.post("/v1/browser/questions")
def browser_question(body: BrowserQuestion, request: Request) -> dict:
    session_hash, device_id = browser_session(request)
    question = body.request.strip()
    if not question:
        raise HTTPException(status_code=400, detail="A question is required.")
    intent = browser_intent(question)
    if intent == "unknown":
        return {"intent": "unknown", "message": "Moon can currently check performance, startup, storage and Downloads, crashes, or current system status on a paired PC."}
    command_id = secrets.token_urlsafe(16)
    with database.connect() as db:
        db.execute("INSERT INTO commands (id, device_id, created_at, command_type, payload, browser_session_hash) VALUES (?, ?, ?, ?, ?, ?)", (command_id, device_id, now(), intent, json.dumps({"request": question}), session_hash))
    return {"intent": intent, "command_id": command_id, "state": "queued", "scope": "read-only"}


@app.get("/v1/browser/commands/{command_id}")
def browser_command_result(command_id: str, request: Request) -> dict:
    session_hash, _ = browser_session(request)
    with database.connect() as db:
        command = db.execute("SELECT id FROM commands WHERE id = ? AND browser_session_hash = ?", (command_id, session_hash)).fetchone()
        if not command:
            raise HTTPException(status_code=404, detail="Command was not found for this paired browser.")
        result = db.execute("SELECT completed_at, result FROM command_results WHERE command_id = ?", (command_id,)).fetchone()
    if not result:
        return {"command_id": command_id, "state": "waiting"}
    return {"command_id": command_id, "state": "completed", "completed_at": result[0], "result": json.loads(result[1])}
