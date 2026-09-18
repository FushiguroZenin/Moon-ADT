from __future__ import annotations

from dera.system.windows_apps import WindowsApplicationsObserver


class StartupProposalPlanner:
    """Creates review-only suggestions; it cannot change startup configuration."""

    OPTIONAL_MARKERS = ("chromeautolaunch", "copilotautolaunch", "edgeautolaunch", "onedrive", "ollama")

    def proposals(self) -> list[dict]:
        entries = WindowsApplicationsObserver().startup_entries()
        return [{"entry": entry, "reason": "This application appears optional at sign-in. Review it before deciding whether to disable it.", "risk_level": "medium", "confirmation_required": True, "state": "review_only", "execution": "not implemented"} for entry in entries if any(marker in entry["name"].lower() for marker in self.OPTIONAL_MARKERS)]
