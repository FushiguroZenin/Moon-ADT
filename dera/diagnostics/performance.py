from __future__ import annotations

from typing import Any

from dera.core.types import Finding


class PerformanceDiagnostic:
    """Deterministic performance findings from a system snapshot."""

    def analyze(self, snapshot: dict[str, Any]) -> list[Finding]:
        findings: list[Finding] = []
        cpu = snapshot["cpu"]["usage_percent"]
        memory = snapshot["memory"]["usage_percent"]
        disk = snapshot["storage"]["usage_percent"]
        findings.append(Finding("cpu.high" if cpu >= 75 else "cpu.normal", "warning" if cpu >= 75 else "info", "CPU usage is high" if cpu >= 75 else "CPU usage is within the normal range", {"usage_percent": cpu}, "Inspect CPU-heavy processes." if cpu >= 75 else None))
        findings.append(Finding("memory.critical" if memory >= 90 else "memory.high" if memory >= 80 else "memory.normal", "critical" if memory >= 90 else "warning" if memory >= 80 else "info", "Memory usage is very high" if memory >= 90 else "Memory usage is high" if memory >= 80 else "Memory usage is within the normal range", {"usage_percent": memory, "available_gb": snapshot["memory"]["available_gb"]}, "Review the largest memory consumers." if memory >= 80 else None))
        findings.append(Finding("storage.low_space" if disk >= 90 else "storage.normal", "warning" if disk >= 90 else "info", "System storage is nearly full" if disk >= 90 else "System storage has sufficient free space", {"usage_percent": disk, "free_gb": snapshot["storage"]["free_gb"]}, "Inspect large directories before removing anything." if disk >= 90 else None))
        if snapshot["top_processes"]:
            findings.append(Finding("process.largest_memory", "info", "Largest measured memory consumer", snapshot["top_processes"][0]))
        return findings
