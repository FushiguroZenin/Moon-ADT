from __future__ import annotations

from dera.diagnostics.crashes import CrashDiagnostic
from dera.memory.task_store import TaskStore
from dera.tasks.task import Task


class ApplicationCrashInvestigation:
    def run(self, application: str) -> Task:
        task = Task(objective=f"Investigate application crashes: {application}")
        store = TaskStore(); store.save(task)
        data, findings = CrashDiagnostic().analyze(application)
        task.observations.append({"tool": "get_application_events", "data": data})
        task.completed_actions.append("Read recent Windows Application crash reports")
        task.findings.extend(finding.to_dict() for finding in findings)
        task.state = "completed"
        task.result = {"summary": "Crash investigation completed.", "recommended_next_step": "Review the recorded event evidence; no repair action has been proposed."}
        store.save(task)
        return task
