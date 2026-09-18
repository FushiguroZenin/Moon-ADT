from __future__ import annotations

from pathlib import Path

from dera.core.types import Finding


class StorageDiagnostic:
    """Read-only size analysis for common user-owned directories."""

    DEFAULT_TARGETS = ("Desktop", "Documents", "Downloads", "Pictures", "Videos")

    def analyze_user_directories(self, limit: int = 10) -> list[Finding]:
        home = Path.home()
        folders: list[dict[str, object]] = []
        for name in self.DEFAULT_TARGETS:
            path = home / name
            if path.exists():
                folders.append({"path": str(path), "size_gb": self._size_gb(path)})
        folders.sort(key=lambda item: float(item["size_gb"]), reverse=True)
        return [Finding("storage.largest_user_directory", "info", "Largest user-accessible directories", {"directories": folders[:limit]}, "Review these folders before removing or moving anything.")]

    @staticmethod
    def _size_gb(path: Path) -> float:
        total = 0
        try:
            for item in path.rglob("*"):
                try:
                    if item.is_file():
                        total += item.stat().st_size
                except OSError:
                    continue
        except OSError:
            return 0.0
        return round(total / 1024**3, 2)
