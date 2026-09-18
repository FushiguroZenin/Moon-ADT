from __future__ import annotations

from dera.core.types import Finding
from dera.system.windows_apps import WindowsApplicationsObserver


class ApplicationsDiagnostic:
    def __init__(self, observer: WindowsApplicationsObserver | None = None) -> None:
        self.observer = observer or WindowsApplicationsObserver()

    def analyze(self) -> tuple[dict, list[Finding]]:
        startup, applications = self.observer.startup_entries(), self.observer.installed_applications()
        data = {"startup_entries": startup, "installed_applications": applications, "installed_application_count": len(applications)}
        severity = "warning" if len(startup) >= 12 else "info"
        title = "Many startup entries detected" if severity == "warning" else "Startup entries inspected"
        recommendation = "Review startup entries before deciding whether any should be disabled." if severity == "warning" else None
        return data, [Finding("applications.startup_entries", severity, title, {"count": len(startup), "entries": startup}, recommendation), Finding("applications.installed", "info", "Installed applications inspected", {"count": len(applications)})]
