from __future__ import annotations

import platform
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil


def _gb(value: int | float) -> float:
    return round(value / 1024**3, 2)


class SystemObserver:
    """Collects system facts; it never diagnoses or modifies the computer."""

    def snapshot(self) -> dict[str, Any]:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(Path.home().anchor)
        return {
            "os": {"system": platform.system(), "release": platform.release()},
            "hostname": socket.gethostname(),
            "cpu": {"usage_percent": psutil.cpu_percent(interval=0.2), "logical_cores": psutil.cpu_count()},
            "memory": {"total_gb": _gb(memory.total), "used_gb": _gb(memory.used), "available_gb": _gb(memory.available), "usage_percent": memory.percent},
            "storage": {"path": Path.home().anchor, "total_gb": _gb(disk.total), "used_gb": _gb(disk.used), "free_gb": _gb(disk.free), "usage_percent": disk.percent},
            "network": {"is_connected": any(stat.isup for stat in psutil.net_if_stats().values())},
            "uptime_seconds": int(time.time() - psutil.boot_time()),
            "booted_at": datetime.fromtimestamp(psutil.boot_time(), tz=timezone.utc).isoformat(),
            "top_processes": self.top_processes(),
        }

    def top_processes(self, limit: int = 10) -> list[dict[str, Any]]:
        # psutil needs an initial reading and a later reading to calculate CPU use.
        processes_to_sample = list(psutil.process_iter())
        for process in processes_to_sample:
            try:
                process.cpu_percent(None)
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
        time.sleep(0.35)

        processes: list[dict[str, Any]] = []
        for process in processes_to_sample:
            try:
                info = process.as_dict(attrs=["pid", "name", "memory_info", "status", "create_time"])
                memory = info.get("memory_info")
                processes.append({"pid": info["pid"], "name": info.get("name") or "unknown", "memory_mb": round((memory.rss if memory else 0) / 1024**2, 1), "cpu_percent": round(process.cpu_percent(None), 1), "state": info.get("status") or "unknown", "started_at": datetime.fromtimestamp(info["create_time"], tz=timezone.utc).isoformat() if info.get("create_time") else None})
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
        return sorted(processes, key=lambda item: item["memory_mb"], reverse=True)[:limit]
