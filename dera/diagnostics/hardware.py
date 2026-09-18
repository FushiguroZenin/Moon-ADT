from __future__ import annotations

from dera.core.types import Finding
from dera.system.hardware import HardwareObserver


class HardwareDiagnostic:
    def analyze(self) -> tuple[dict, list[Finding]]:
        data = {"battery": HardwareObserver().battery(), "network": HardwareObserver().network(), "gpu": HardwareObserver().gpu()}
        findings: list[Finding] = []
        battery = data["battery"]
        if battery["available"] and battery["percent"] <= 20 and not battery["plugged_in"]:
            findings.append(Finding("battery.low", "warning", "Battery level is low", battery, "Connect power if you need to continue working."))
        else:
            findings.append(Finding("battery.status", "info", "Battery status inspected", battery))
        up = [name for name, item in data["network"]["interfaces"].items() if item["is_up"]]
        findings.append(Finding("network.interfaces", "info", "Network interfaces inspected", {"active_interfaces": up, "bytes_received": data["network"]["bytes_received"]}))
        findings.append(Finding("gpu.status", "info", "GPU telemetry inspected", data["gpu"]))
        return data, findings
