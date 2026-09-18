from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import uuid4

from dera.system.directory_inspector import DirectoryInspector


@dataclass(frozen=True)
class CleanupProposal:
    id: str
    path: str
    reclaimable_gb: float
    action_options: tuple[str]
    reason: str
    risk_level: str = "high"
    confirmation_required: bool = True
    state: str = "proposed"

    def to_dict(self) -> dict:
        return asdict(self)


class CleanupProposalPlanner:
    """Creates reviewable proposals only. It never changes a file."""

    def __init__(self, inspector: DirectoryInspector | None = None) -> None:
        self.inspector = inspector or DirectoryInspector()

    def for_downloads(self, minimum_gb: float = 1.0, limit: int = 10) -> list[CleanupProposal]:
        downloads = Path.home() / "Downloads"
        analysis = self.inspector.inspect(downloads, limit=limit)
        proposals: list[CleanupProposal] = []
        for folder in analysis["largest_subfolders"]:
            if folder["name"] == "(files in this folder)" or folder["size_gb"] < minimum_gb:
                continue
            target = downloads / folder["name"]
            proposals.append(CleanupProposal(
                id=str(uuid4()),
                path=str(target),
                reclaimable_gb=folder["size_gb"],
                action_options=("move to a user-selected location", "copy to a user-selected location"),
                reason="This is one of the largest folders in Downloads while system storage is under pressure.",
            ))
        return proposals
