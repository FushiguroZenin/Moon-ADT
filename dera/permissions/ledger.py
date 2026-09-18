from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from dera.paths import database_path as moon_database_path


class PermissionLedger:
    """Records explicit, proposal-specific approval before controlled actions."""

    def __init__(self, database_path: Path | None = None) -> None:
        self.database_path = database_path or moon_database_path()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS proposals (id TEXT PRIMARY KEY, payload TEXT NOT NULL, approved_action TEXT, destination TEXT, executed INTEGER NOT NULL DEFAULT 0)")

    def save_proposals(self, proposals: list[dict]) -> None:
        with sqlite3.connect(self.database_path) as db:
            db.executemany("INSERT OR REPLACE INTO proposals (id, payload, approved_action, destination, executed) VALUES (?, ?, NULL, NULL, 0)", [(item["id"], json.dumps(item)) for item in proposals])

    def approve_move(self, proposal_id: str, destination: str) -> None:
        self._approve(proposal_id, "move", destination)

    def approve_copy(self, proposal_id: str, destination: str) -> None:
        self._approve(proposal_id, "copy", destination)

    def _approve(self, proposal_id: str, action: str, destination: str) -> None:
        with sqlite3.connect(self.database_path) as db:
            updated = db.execute("UPDATE proposals SET approved_action = ?, destination = ? WHERE id = ? AND executed = 0", (action, destination, proposal_id)).rowcount
            if updated != 1:
                raise ValueError("Proposal was not found or has already been executed.")

    def dismiss(self, proposal_id: str) -> None:
        """Remove an unacted proposal from the local action queue only."""
        with sqlite3.connect(self.database_path) as db:
            removed = db.execute("DELETE FROM proposals WHERE id = ? AND executed = 0", (proposal_id,)).rowcount
            if removed != 1:
                raise ValueError("Proposal was not found or has already been executed.")

    def approved(self, proposal_id: str) -> dict:
        return self.approved_for(proposal_id, "move")

    def approved_for(self, proposal_id: str, action: str) -> dict:
        proposal = self.get(proposal_id)
        if proposal["approved_action"] != action:
            raise ValueError(f"This proposal has not been approved for a {action}.")
        return proposal

    def get(self, proposal_id: str) -> dict:
        with sqlite3.connect(self.database_path) as db:
            row = db.execute("SELECT payload, approved_action, destination, executed FROM proposals WHERE id = ?", (proposal_id,)).fetchone()
        if not row or row[3]:
            raise ValueError("Proposal was not found or has already been executed.")
        proposal = json.loads(row[0]); proposal["destination"] = row[2]
        proposal["approved_action"] = row[1]
        return proposal

    def mark_executed(self, proposal_id: str) -> None:
        with sqlite3.connect(self.database_path) as db:
            db.execute("UPDATE proposals SET executed = 1 WHERE id = ?", (proposal_id,))
