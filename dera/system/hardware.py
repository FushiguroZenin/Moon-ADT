from __future__ import annotations

import shutil
import subprocess
from typing import Any

import psutil


class HardwareObserver:
    """Read-only battery, GPU, and network observation."""

    def battery(self) -> dict[str, Any]:
        battery = psutil.sensors_battery()
        if battery is None:
            return {"available": False}
        return {"available": True, "percent": battery.percent, "plugged_in": battery.power_plugged, "seconds_remaining": battery.secsleft if battery.secsleft >= 0 else None}

    def network(self) -> dict[str, Any]:
        counters = psutil.net_io_counters()
        interfaces = {name: {"is_up": stat.isup, "speed_mbps": stat.speed} for name, stat in psutil.net_if_stats().items()}
        return {"interfaces": interfaces, "bytes_sent": counters.bytes_sent, "bytes_received": counters.bytes_recv}

    def gpu(self) -> dict[str, Any]:
        executable = shutil.which("nvidia-smi")
        if not executable:
            return {"available": False, "reason": "NVIDIA GPU telemetry is not available."}
        try:
            output = subprocess.run([executable, "--query-gpu=name,driver_version,memory.used,memory.total,utilization.gpu", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10, check=False).stdout.strip()
            rows = [{"name": fields[0], "driver_version": fields[1], "memory_used_mb": fields[2], "memory_total_mb": fields[3], "utilization_percent": fields[4]} for line in output.splitlines() if len(fields := [value.strip() for value in line.split(",")]) == 5]
            return {"available": bool(rows), "gpus": rows}
        except (OSError, subprocess.TimeoutExpired):
            return {"available": False, "reason": "GPU telemetry query failed."}
