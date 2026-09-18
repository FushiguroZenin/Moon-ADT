from __future__ import annotations

from dera.diagnostics.performance import PerformanceDiagnostic
from dera.diagnostics.storage import StorageDiagnostic
from dera.memory.task_store import TaskStore
from dera.system.observer import SystemObserver
from dera.tasks.task import Task


class SlowComputerInvestigation:
    """A deterministic, read-only investigation for perceived slowness."""

    def __init__(self, observer: SystemObserver | None = None, store: TaskStore | None = None) -> None:
        self.observer = observer or SystemObserver()
        self.store = store or TaskStore()

    def run(self) -> Task:
        task = Task(objective="Investigate why the computer is slow")
        self.store.save(task)
        snapshot = self.observer.snapshot()
        task.observations.append({"tool": "get_system_status", "data": snapshot})
        task.completed_actions.append("Captured system state")
        performance_findings = PerformanceDiagnostic().analyze(snapshot)
        task.findings.extend(finding.to_dict() for finding in performance_findings)

        if snapshot["storage"]["usage_percent"] >= 90:
            task.pending_actions.append("Inspect user-accessible storage")
            storage_findings = StorageDiagnostic().analyze_user_directories()
            task.findings.extend(finding.to_dict() for finding in storage_findings)
            task.completed_actions.append("Inspected user-accessible storage")
            task.pending_actions.remove("Inspect user-accessible storage")

        warnings = [finding for finding in task.findings if finding["severity"] in {"warning", "critical"}]
        task.state = "completed"
        task.result = {
            "summary": "Investigation completed with evidence-backed findings.",
            "highest_severity": "critical" if any(finding["severity"] == "critical" for finding in warnings) else "warning" if warnings else "info",
            "recommended_next_step": self._recommend(snapshot),
        }
        self.store.save(task)
        return task

    @staticmethod
    def _recommend(snapshot: dict) -> str:
        if snapshot["storage"]["usage_percent"] >= 90:
            return "Review the largest user-accessible directories and choose folders to move to a user-selected location. Moon will require permission before changing anything."
        if snapshot["memory"]["usage_percent"] >= 80:
            return "Review the largest memory consumers and close only applications you no longer need."
        if snapshot["cpu"]["usage_percent"] >= 75:
            return "Inspect CPU-heavy processes over a longer sample window."
        return "No dominant issue was detected in this snapshot; collect another sample while slowness is occurring."
