from __future__ import annotations

import shutil
from pathlib import Path

from dera.permissions.ledger import PermissionLedger


class ControlledMove:
    """Moves an explicitly approved proposal and verifies its result."""

    def preview(self, proposal_id: str, destination: str | None = None, require_approval: bool = False) -> dict:
        proposal = PermissionLedger().approved(proposal_id) if require_approval else PermissionLedger().get(proposal_id)
        if destination is not None:
            proposal["destination"] = destination
        if not proposal["destination"]:
            raise ValueError("A destination directory is required for this preview.")
        home = Path.home().resolve()
        source, destination_root = Path(proposal["path"]).resolve(), Path(proposal["destination"]).resolve()
        if home not in source.parents or (destination_root != home and home not in destination_root.parents):
            raise ValueError("Source and destination must be inside the current user's home directory.")
        if not source.exists():
            raise ValueError(f"The proposed source no longer exists: {source}")
        if not destination_root.exists():
            raise ValueError(f"The destination directory does not exist: {destination_root}. Create it first, then run preview again.")
        if not destination_root.is_dir():
            raise ValueError(f"The destination is not a directory: {destination_root}")
        target = destination_root / source.name
        if target.exists():
            raise ValueError("Destination already contains an item with this name.")
        return {"proposal_id": proposal_id, "action": "move", "source": str(source), "destination": str(target), "estimated_size_gb": proposal["reclaimable_gb"], "validated": True, "dry_run": True, "message": "No files were moved."}

    def execute(self, proposal_id: str) -> dict:
        preview = self.preview(proposal_id, require_approval=True)
        source, destination_root = Path(preview["source"]), Path(preview["destination"]).parent
        before = shutil.disk_usage(source.anchor).free
        shutil.move(str(source), str(destination_root))
        target = Path(preview["destination"])
        if source.exists() or not target.exists():
            raise RuntimeError("Move could not be verified.")
        after = shutil.disk_usage(target.anchor).free
        PermissionLedger().mark_executed(proposal_id)
        return {"proposal_id": proposal_id, "source": str(source), "destination": str(target), "verified": True, "free_space_change_gb": round((after - before) / 1024**3, 2)}
