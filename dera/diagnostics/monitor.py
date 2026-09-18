from __future__ import annotations

from datetime import datetime, timezone

from dera.memory.monitor_store import MonitorStore
from dera.system.observer import SystemObserver
from dera.system.windows_apps import WindowsApplicationsObserver


class Monitor:
    STORAGE_DROP_GB = 5.0
    HIGH_MEMORY_PERCENT = 85.0

    def __init__(self, store: MonitorStore | None = None) -> None:
        self.store = store or MonitorStore()

    def check(self) -> dict:
        previous = self.store.latest()
        system = SystemObserver().snapshot()
        current = {"observed_at": datetime.now(timezone.utc).isoformat(), "storage_free_gb": system["storage"]["free_gb"], "memory_percent": system["memory"]["usage_percent"], "startup_names": sorted(entry["name"] for entry in WindowsApplicationsObserver().startup_entries())}
        findings: list[dict] = []
        if previous:
            storage_drop = previous["storage_free_gb"] - current["storage_free_gb"]
            if storage_drop >= self.STORAGE_DROP_GB:
                findings.append({"code": "monitor.storage_drop", "severity": "warning", "message": f"Free storage decreased by {storage_drop:.2f} GB since the previous check."})
            new_startup = sorted(set(current["startup_names"]) - set(previous["startup_names"]))
            if new_startup:
                findings.append({"code": "monitor.new_startup", "severity": "warning", "message": "New startup entries detected.", "entries": new_startup})
        if current["memory_percent"] >= self.HIGH_MEMORY_PERCENT:
            findings.append({"code": "monitor.high_memory", "severity": "warning", "message": f"Memory usage is currently high at {current['memory_percent']}%."})
        self.store.save(current)
        self.store.record_check(findings, current["observed_at"])
        return {"baseline_exists": previous is not None, "snapshot": current, "findings": findings, "message": "No meaningful change detected." if not findings else "Meaningful changes detected. No action was taken."}
