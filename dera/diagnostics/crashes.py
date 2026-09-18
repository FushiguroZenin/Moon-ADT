from __future__ import annotations

from dera.core.types import Finding
from dera.system.windows_events import WindowsEventObserver


class CrashDiagnostic:
    def __init__(self, observer: WindowsEventObserver | None = None) -> None:
        self.observer = observer or WindowsEventObserver()

    def analyze(self, application: str) -> tuple[dict, list[Finding]]:
        events = self.observer.recent_application_errors(application)
        severity = "warning" if events else "info"
        title = "Recent crash reports found" if events else "No recent matching crash reports found"
        return {"application": application, "events": events}, [Finding("applications.crash_events", severity, title, {"application": application, "count": len(events), "events": events}, "Review faulting modules and timestamps before proposing any repair." if events else None)]
