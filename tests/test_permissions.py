from pathlib import Path

import pytest

from dera.permissions.ledger import PermissionLedger


def test_dismissed_proposal_cannot_be_approved(tmp_path: Path) -> None:
    ledger = PermissionLedger(tmp_path / "moon.db")
    ledger.save_proposals([{"id": "proposal-1", "path": "C:\\Users\\Test\\Downloads\\item", "reclaimable_gb": 1}])
    ledger.dismiss("proposal-1")
    with pytest.raises(ValueError):
        ledger.approve_move("proposal-1", "C:\\Users\\Test\\Documents")
