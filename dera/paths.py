"""Stable storage locations for source and installed Moon runtimes."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def data_directory() -> Path:
    configured = os.getenv("MOON_DATA_DIR")
    if configured:
        path = Path(configured)
    elif getattr(sys, "frozen", False):
        path = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Moon" / "data"
    else:
        path = Path("data")
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    return data_directory() / "moon.db"


def log_directory() -> Path:
    root = data_directory().parent if data_directory().name == "data" else data_directory()
    path = root / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
