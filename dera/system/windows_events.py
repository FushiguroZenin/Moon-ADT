from __future__ import annotations

import re
import subprocess
from typing import Any


class WindowsEventObserver:
    """Read-only reader for recent Windows Application crash reports."""

    def recent_application_errors(self, application: str, limit: int = 30) -> list[dict[str, Any]]:
        if not re.fullmatch(r"[A-Za-z0-9_. -]{1,80}", application):
            raise ValueError("Application name contains unsupported characters.")
        command = ["wevtutil", "qe", "Application", "/q:*[System[(EventID=1000 or EventID=1001)]]", "/f:RenderedText", f"/c:{limit}", "/rd:true"]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise RuntimeError("Windows Application event log could not be read.") from error
        events: list[dict[str, Any]] = []
        for block in re.split(r"\r?\n\r?\n", completed.stdout):
            if application.lower() not in block.lower():
                continue
            event_id = re.search(r"Event ID:\s*(\d+)", block)
            date = re.search(r"Date:\s*(.+)", block)
            faulting = re.search(r"Faulting application name:\s*([^,\r\n]+)", block, re.I)
            module = re.search(r"Faulting module name:\s*([^,\r\n]+)", block, re.I)
            events.append({"event_id": event_id.group(1) if event_id else "unknown", "date": date.group(1).strip() if date else "unknown", "faulting_application": faulting.group(1).strip() if faulting else application, "faulting_module": module.group(1).strip() if module else "unknown", "raw": block.strip()})
        return events
