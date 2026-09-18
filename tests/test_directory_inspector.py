from pathlib import Path

import pytest

from dera.system.directory_inspector import DirectoryInspector


def test_rejects_paths_outside_user_home() -> None:
    with pytest.raises(ValueError, match="limited"):
        DirectoryInspector().inspect(Path.home().anchor)
