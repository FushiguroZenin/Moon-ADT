from __future__ import annotations

import heapq
import os
from collections import Counter
from pathlib import Path
from typing import Any


class DirectoryInspector:
    """Read-only directory analysis limited to the current user's home folder."""

    def inspect(self, requested_path: str | Path, limit: int = 20) -> dict[str, Any]:
        path = Path(requested_path).expanduser().resolve()
        home = Path.home().resolve()
        if path != home and home not in path.parents:
            raise ValueError("Directory inspection is limited to the current user's home directory.")
        if not path.is_dir():
            raise ValueError(f"Not a directory: {path}")

        largest_files: list[tuple[int, str]] = []
        top_level_sizes: Counter[str] = Counter()
        extension_sizes: Counter[str] = Counter()
        file_count = 0
        unreadable_items = 0
        for root, _, names in os.walk(path, onerror=lambda _: None):
            for name in names:
                file_path = Path(root) / name
                try:
                    size = file_path.stat().st_size
                except OSError:
                    unreadable_items += 1
                    continue
                file_count += 1
                relative = file_path.relative_to(path)
                bucket = relative.parts[0] if len(relative.parts) > 1 else "(files in this folder)"
                top_level_sizes[bucket] += size
                extension_sizes[file_path.suffix.lower() or "(no extension)"] += size
                heapq.heappush(largest_files, (size, str(file_path)))
                if len(largest_files) > limit:
                    heapq.heappop(largest_files)

        return {
            "path": str(path),
            "file_count": file_count,
            "unreadable_items": unreadable_items,
            "total_size_gb": round(sum(top_level_sizes.values()) / 1024**3, 2),
            "largest_files": [{"path": file_path, "size_gb": round(size / 1024**3, 2), "size_mb": round(size / 1024**2, 1)} for size, file_path in sorted(largest_files, reverse=True)],
            "largest_subfolders": [{"name": name, "size_gb": round(size / 1024**3, 2)} for name, size in top_level_sizes.most_common(limit)],
            "largest_file_types": [{"extension": extension, "size_gb": round(size / 1024**3, 2)} for extension, size in extension_sizes.most_common(limit)],
        }
