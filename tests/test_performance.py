from dera.diagnostics.performance import PerformanceDiagnostic


def test_detects_critical_memory_pressure() -> None:
    snapshot = {"cpu": {"usage_percent": 20}, "memory": {"usage_percent": 92, "available_gb": 1}, "storage": {"usage_percent": 50, "free_gb": 50}, "top_processes": []}
    findings = PerformanceDiagnostic().analyze(snapshot)
    assert any(finding.code == "memory.critical" for finding in findings)
