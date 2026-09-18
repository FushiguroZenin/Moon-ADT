from __future__ import annotations

from pathlib import Path
import re

from dera.diagnostics.applications import ApplicationsDiagnostic
from dera.system.directory_inspector import DirectoryInspector
from dera.system.observer import SystemObserver
from dera.tasks.application_crash import ApplicationCrashInvestigation
from dera.tasks.slow_computer import SlowComputerInvestigation
from dera.models.ollama import OllamaProvider
from dera.models.conversation import GroundedConversation
from dera.models.provider import ModelUnavailable


class RelayReadOnlyDispatcher:
    """Maps relay commands to the same local, read-only Dera1.4 handlers."""

    ALLOWED = {
        "system_status",
        "investigate_slow_computer",
        "inspect_downloads",
        "diagnose_startup_applications",
        "investigate_application_crash",
    }

    def dispatch(self, command: dict) -> dict:
        kind = command.get("command_type")
        if kind not in self.ALLOWED:
            return {"state": "rejected", "reason": "Relay command is not in Dera1.4's read-only allow-list."}
        payload = command.get("payload") or {}
        if kind == "system_status":
            return {"state": "completed", "result": {"snapshot": SystemObserver().snapshot()}}
        if kind == "investigate_slow_computer":
            task = SlowComputerInvestigation().run()
            conversation = None
            try:
                conversation = GroundedConversation(OllamaProvider()).respond(str(payload.get("request", "")), task)
            except ModelUnavailable:
                pass
            return {"state": "completed", "result": {"task": task.to_dict(), "conversation": conversation}}
        if kind == "inspect_downloads":
            return {"state": "completed", "result": {"inspection": DirectoryInspector().inspect(Path.home() / "Downloads")}}
        if kind == "diagnose_startup_applications":
            data, findings = ApplicationsDiagnostic().analyze()
            return {"state": "completed", "result": {"data": data, "findings": [finding.to_dict() for finding in findings]}}
        application = str(payload.get("application", "")).strip()
        if not application:
            request = str(payload.get("request", ""))
            match = re.search(r"(?:my )?([A-Za-z0-9_.-]+)\s+(?:keep(?:s)?\s+)?(?:crash|crashes|crashing|keeps closing|closed unexpectedly|stopped working)", request, re.IGNORECASE)
            application = match.group(1) if match else ""
        if not application:
            return {"state": "needs_input", "reason": "An application name is required for crash investigation."}
        return {"state": "completed", "result": {"task": ApplicationCrashInvestigation().run(application).to_dict()}}
