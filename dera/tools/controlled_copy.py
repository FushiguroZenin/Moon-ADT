from __future__ import annotations

import shutil
from pathlib import Path

from dera.permissions.ledger import PermissionLedger


class ControlledCopy:
    """Copies an explicitly approved proposal and verifies the copy."""

    def preview(self, proposal_id: str, destination: str | None = None, require_approval: bool = False) -> dict:
        ledger = PermissionLedger()
        proposal = ledger.approved_for(proposal_id, "copy") if require_approval else ledger.get(proposal_id)
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
        if not destination_root.is_dir():
            raise ValueError("The destination must be an existing directory.")
        target = destination_root / source.name
        if target.exists():
            raise ValueError("Destination already contains an item with this name.")
        required = self._size(source)
        available = shutil.disk_usage(destination_root).free
        if available < required:
            raise ValueError("The destination does not have enough free space for this copy.")
        return {"proposal_id": proposal_id, "action": "copy", "source": str(source), "destination": str(target), "estimated_size_gb": proposal["reclaimable_gb"], "validated": True, "dry_run": True, "message": "No files were copied."}

    def execute(self, proposal_id: str) -> dict:
        preview = self.preview(proposal_id, require_approval=True)
        source, target = Path(preview["source"]), Path(preview["destination"])
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
        if not target.exists() or self._size(source) != self._size(target):
            raise RuntimeError("Copy could not be verified.")
        PermissionLedger().mark_executed(proposal_id)
        return {"proposal_id": proposal_id, "source": str(source), "destination": str(target), "verified": True, "source_preserved": source.exists(), "copied_size_gb": round(self._size(target) / 1024**3, 2)}

    @staticmethod
    def _size(path: Path) -> int:
        if path.is_file():
            return path.stat().st_size
        return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())
