"""Local-only HTTP surface for Moon's Dera1.4 runtime."""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
import sys
from threading import Event, Thread
from datetime import datetime, timezone
import os
import shutil
import subprocess
import json
from urllib.error import URLError
import socket
from urllib.request import Request, urlopen

from dera.diagnostics.monitor import Monitor
from dera.memory.monitor_store import MonitorStore
from dera.memory.task_store import TaskStore
from dera.permissions.ledger import PermissionLedger
from dera.system.directory_inspector import DirectoryInspector
from dera.system.observer import SystemObserver
from dera.system.startup_preference import StartupPreference
from dera.tasks.cleanup_proposals import CleanupProposalPlanner
from dera.tasks.slow_computer import SlowComputerInvestigation
from dera.tasks.router import IntentRouter
from dera.models.ollama import OllamaProvider
from dera.models.provider import ModelUnavailable
from dera.models.conversation import GroundedConversation
from dera.models.interpreter import InvestigationInterpreter
from dera.diagnostics.applications import ApplicationsDiagnostic
from dera.tasks.application_crash import ApplicationCrashInvestigation
from dera.relay.client import OutboundRelayClient
from dera.relay.store import RelayStore
from dera.relay.dispatcher import RelayReadOnlyDispatcher
import re
from dera.tools.controlled_move import ControlledMove
from dera.tools.controlled_copy import ControlledCopy
from dera.permissions.pairing import PairingService

def _frontend_directory() -> Path:
    """Resolve bundled assets in a PyInstaller build and source assets in development."""
    bundled_root = getattr(sys, "_MEIPASS", None)
    return Path(bundled_root) / "frontend" if bundled_root else Path(__file__).resolve().parents[2] / "frontend"


app = FastAPI(title="Moon local runtime", version="0.1.0", docs_url="/docs")
app.mount("/app", StaticFiles(directory=_frontend_directory(), html=True), name="moon_app")
_runtime_started_at = datetime.now(timezone.utc).isoformat()
_ai_download_state = {"state": "idle", "status": "Not started", "completed": 0, "total": 0, "error": None}
_ai_download_lock = Event()
_monitor_stop = Event()
_monitor_wake = Event()
_relay_stop = Event()
_relay_wake = Event()


def _require_local_actions_enabled() -> None:
    if os.getenv("MOON_GUIDANCE_ONLY") == "1":
        raise HTTPException(status_code=403, detail="Moon V1 is in guidance-only mode. Review the recommended manual steps; file changes are disabled.")


def _monitor_worker() -> None:
    """Run only while this localhost runtime is alive and monitoring is opted in."""
    while not _monitor_stop.is_set():
        settings = MonitorStore().settings()
        if settings["enabled"]:
            Monitor().check()
            wait_seconds = max(5 * 60, settings["interval_minutes"] * 60)
        else:
            wait_seconds = 60
        _monitor_wake.wait(wait_seconds)
        _monitor_wake.clear()


def _process_relay_commands() -> list[dict]:
    client = OutboundRelayClient()
    polled = client.poll_commands()
    completed: list[dict] = []
    for command in polled.get("commands", []):
        result = RelayReadOnlyDispatcher().dispatch(command)
        client.send_result(command.get("id", ""), result)
        completed.append({"command_id": command.get("id"), "state": result["state"]})
    return completed


def _relay_worker() -> None:
    """Publish read-only evidence outward while retaining the future command poll."""
    while not _relay_stop.is_set():
        if RelayStore().get()["enabled"]:
            try:
                client = OutboundRelayClient()
                heartbeat = client.heartbeat()
                if heartbeat.get("sent"):
                    client.publish_snapshot(SystemObserver().snapshot())
                _process_relay_commands()
            except Exception:
                # The next scheduled outbound attempt can recover from a transient relay failure.
                pass
            # A paired browser reads the latest snapshot directly from the relay.
            wait_seconds = 5
        else:
            wait_seconds = 60
        _relay_wake.wait(wait_seconds)
        _relay_wake.clear()


def _application_from_request(request: str) -> str | None:
    patterns = (
        r"(?:why did |check |investigate )?(?:my )?([A-Za-z0-9_.-]+)\s+(?:keep(?:s)?\s+)?crash",
        r"crash(?:ing|es)?\s+(?:for |in |with )?([A-Za-z0-9_.-]+)",
        r"([A-Za-z0-9_.-]+)\s+(?:closed unexpectedly|stopped working|keeps closing)",
    )
    for pattern in patterns:
        match = re.search(pattern, request, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


@app.on_event("startup")
def start_monitor_worker() -> None:
    _monitor_stop.clear()
    _monitor_wake.clear()
    Thread(target=_monitor_worker, daemon=True, name="moon-local-monitor").start()
    _relay_stop.clear()
    _relay_wake.clear()
    Thread(target=_relay_worker, daemon=True, name="moon-outbound-relay").start()


@app.on_event("shutdown")
def stop_monitor_worker() -> None:
    _monitor_stop.set()
    _monitor_wake.set()
    _relay_stop.set()
    _relay_wake.set()


class FollowUp(BaseModel):
    request: str


class AskRequest(BaseModel):
    request: str


class TaskFollowUp(BaseModel):
    request: str


class MonitoringConfig(BaseModel):
    enabled: bool
    interval_minutes: int = 30


class StartupPreferenceConfig(BaseModel):
    enabled: bool


class RelayConfig(BaseModel):
    relay_url: str | None = None
    enabled: bool = False


class MovePreview(BaseModel):
    destination: str


class MoveApproval(BaseModel):
    destination: str
    confirmed: bool = False


class PairingCompletion(BaseModel):
    code: str
    client_name: str


@app.get("/")
def home() -> dict:
    return {"service": "Moon local runtime", "status": "running", "docs": "/docs", "api": {"status": "/status", "tasks": "/tasks", "monitor": "/monitor/check"}}


@app.get("/runtime/health")
def runtime_health() -> dict:
    ollama = OllamaProvider().status()
    return {
        "status": "running",
        "started_at": _runtime_started_at,
        "address": "http://127.0.0.1:8765",
        "data_directory": os.getenv("MOON_DATA_DIR", str(Path("data").resolve())),
        "ollama": ollama,
        "actions_mode": "guidance-only" if os.getenv("MOON_GUIDANCE_ONLY") == "1" else "controlled-local-actions",
    }


def _ollama_executable() -> str | None:
    return shutil.which("ollama") or next((str(path) for path in [Path(os.getenv("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"] if path.is_file()), None)


@app.get("/local-ai/status")
def local_ai_status() -> dict:
    provider = OllamaProvider()
    status = provider.status()
    data_root = Path(os.getenv("MOON_DATA_DIR", str(Path("data").resolve())))
    free_gb = round(shutil.disk_usage(data_root.anchor or data_root).free / (1024 ** 3), 2)
    return {**status, "ollama_installed": bool(_ollama_executable()), "download": _ai_download_state.copy(), "free_gb": free_gb}


def _pull_local_model(provider: OllamaProvider) -> None:
    global _ai_download_state
    try:
        request = Request(f"{provider.base_url}/api/pull", data=json.dumps({"name": provider.model, "stream": True}).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=600) as response:
            for line in response:
                if not line.strip():
                    continue
                event = json.loads(line)
                _ai_download_state.update({"state": "downloading", "status": event.get("status", "Preparing local AI"), "completed": int(event.get("completed", 0)), "total": int(event.get("total", 0)), "error": event.get("error")})
                if event.get("error"):
                    _ai_download_state["state"] = "failed"
                    return
        _ai_download_state.update({"state": "complete", "status": "Moon’s local AI is ready.", "error": None})
    except (URLError, OSError, ValueError, json.JSONDecodeError) as error:
        reason = str(error)
        dns_failure = isinstance(error, socket.gaierror) or "no such host" in reason.lower() or "name or service not known" in reason.lower()
        detail = (
            "Moon could not reach Ollama’s model download service. Check your internet or DNS connection, try another network if available, then retry."
            if dns_failure
            else "Moon could not download the local AI. Check your internet connection, then retry."
        )
        _ai_download_state.update({"state": "failed", "status": detail, "error": "Network name lookup failed." if dns_failure else reason[:240]})
    finally:
        _ai_download_lock.clear()


@app.post("/local-ai/download-model")
def download_local_ai_model() -> dict:
    """Start the optional, user-confirmed local model download without a shell."""
    executable = _ollama_executable()
    if not executable:
        raise HTTPException(status_code=409, detail="Install Ollama first, then return to Moon to download its recommended local AI.")
    if _ai_download_lock.is_set():
        return {"state": "downloading", "model": OllamaProvider().model}
    provider = OllamaProvider()
    _ai_download_state.update({"state": "starting", "status": "Starting Moon’s local AI download…", "completed": 0, "total": 0, "error": None})
    _ai_download_lock.set()
    Thread(target=_pull_local_model, args=(provider,), daemon=True, name="moon-local-ai-download").start()
    return {"state": "starting", "model": provider.model}


@app.get("/pairing/status")
def pairing_status() -> dict:
    return PairingService().status()


@app.post("/pairing/code")
def create_pairing_code() -> dict:
    code = PairingService().create_code()
    relay = OutboundRelayClient().heartbeat()
    code["relay_synced"] = bool(relay.get("sent"))
    return code


@app.post("/pairing/complete")
def complete_pairing(body: PairingCompletion) -> dict:
    try:
        return PairingService().complete(body.code, body.client_name)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/pairing/browsers")
def paired_browsers() -> dict:
    return OutboundRelayClient().browser_sessions()


@app.delete("/pairing/browsers/{client_id}")
def revoke_paired_browser(client_id: str) -> dict:
    result = OutboundRelayClient().revoke_browser_session(client_id)
    if not result.get("revoked"):
        raise HTTPException(status_code=400, detail=result.get("message", "Paired browser could not be revoked."))
    return result


@app.get("/status")
def status() -> dict:
    return SystemObserver().snapshot()


@app.get("/system/startup")
def system_startup() -> dict:
    """Read-only startup-application evidence for the local System view."""
    data, findings = ApplicationsDiagnostic().analyze()
    return {"data": data, "findings": [finding.to_dict() for finding in findings]}


@app.get("/settings/local")
def local_settings() -> dict:
    return {
        "runtime": {"address": "http://127.0.0.1:8765", "scope": "local computer only"},
        "ollama": OllamaProvider().status(),
        "pairing": PairingService().status(),
        "monitoring": {"mode": "manual local checks", "description": "Moon does not run a background scheduler or send notifications yet."},
        "permissions": {"description": "Moon requires a proposal, explicit approval, validation, and a separate execution step before a change."},
        "relay": RelayStore().get(),
        "startup": StartupPreference().status(),
    }


@app.post("/settings/start-with-windows")
def update_start_with_windows(body: StartupPreferenceConfig) -> dict:
    try:
        return StartupPreference().set_enabled(body.enabled)
    except RuntimeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/relay/settings")
def relay_settings() -> dict:
    return RelayStore().get()


@app.post("/relay/settings")
def update_relay_settings(body: RelayConfig) -> dict:
    if body.enabled and (not body.relay_url or not body.relay_url.startswith("https://")):
        raise HTTPException(status_code=400, detail="An HTTPS relay URL is required before outbound relay can be enabled.")
    settings = RelayStore().configure(body.relay_url.rstrip("/") if body.relay_url else None, body.enabled)
    _relay_wake.set()
    return settings


@app.post("/relay/heartbeat")
def relay_heartbeat() -> dict:
    return OutboundRelayClient().heartbeat()


@app.post("/relay/poll")
def relay_poll() -> dict:
    return {"processed": _process_relay_commands()}


@app.post("/tasks/slow-computer")
def investigate_slow_computer() -> dict:
    return SlowComputerInvestigation().run().to_dict()


@app.post("/ask")
def ask_moon(body: AskRequest) -> dict:
    """Run one allow-listed, read-only request from Moon's conversation UI."""
    request = body.request.strip()
    if not request:
        raise HTTPException(status_code=400, detail="A request is required.")
    try:
        intent = IntentRouter(OllamaProvider()).route(request)
    except ModelUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    conversation: dict | None = None
    if intent == "system_status":
        result: dict = {"snapshot": SystemObserver().snapshot(), "findings": []}
    elif intent == "investigate_slow_computer":
        task = SlowComputerInvestigation().run()
        result = {"task": task.to_dict()}
        try:
            conversation = GroundedConversation(OllamaProvider()).respond(request, task)
        except ModelUnavailable:
            # The deterministic task result remains a safe, useful fallback.
            conversation = None
    elif intent == "explain_slow_computer":
        task = SlowComputerInvestigation().run()
        try:
            explanation = InvestigationInterpreter(OllamaProvider()).explain(task)
        except ModelUnavailable:
            explanation = {"interpretation": task.result["summary"], "next_step": task.result["recommended_next_step"], "evidence": task.findings, "grounded": False}
        result = {"task": task.to_dict(), "explanation": explanation}
    elif intent == "diagnose_startup_applications":
        data, findings = ApplicationsDiagnostic().analyze()
        result = {"data": data, "findings": [finding.to_dict() for finding in findings]}
    elif intent == "investigate_application_crash":
        application = _application_from_request(request)
        if not application:
            result = {"needs_application_name": True, "message": "Which application should I investigate? For example, say: Chrome keeps crashing."}
        else:
            task = ApplicationCrashInvestigation().run(application)
            result = {"task": task.to_dict(), "application": application}
    elif intent == "inspect_downloads":
        result = {"inspection": DirectoryInspector().inspect(Path.home() / "Downloads")}
    elif intent == "inspect_user_folders":
        result = {"inspection": DirectoryInspector().inspect(Path.home())}
    elif intent == "review_downloads_proposals":
        proposals = [proposal.to_dict() for proposal in CleanupProposalPlanner().for_downloads()]
        PermissionLedger().save_proposals(proposals)
        result = {"proposals": proposals, "execution": "disabled"}
    else:
        result = {
            "message": "I am not sure which safe investigation fits that request. Do you want me to check system performance, startup applications, storage and Downloads, or the current system status? If you want Moon to change anything, it must first prepare a proposal and receive your explicit approval.",
            "execution": "disabled",
        }
    return {"request": request, "intent": intent, "result": result, "conversation": conversation}


@app.post("/tasks/{task_id}/follow-up")
def continue_task_conversation(task_id: str, body: TaskFollowUp) -> dict:
    """Attach an allow-listed, read-only follow-up to an existing local task."""
    request = body.request.strip()
    if not request:
        raise HTTPException(status_code=400, detail="A follow-up request is required.")
    store = TaskStore()
    try:
        store.get(task_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    try:
        intent = IntentRouter(OllamaProvider()).route(request)
    except ModelUnavailable:
        intent = "unknown"

    conversation: dict | None = None
    if intent == "system_status":
        evidence: dict = {"snapshot": SystemObserver().snapshot(), "findings": []}
    elif intent == "investigate_slow_computer":
        task = SlowComputerInvestigation().run()
        evidence = {"task": task.to_dict()}
        try:
            conversation = GroundedConversation(OllamaProvider()).respond(request, task)
        except ModelUnavailable:
            conversation = None
    elif intent == "explain_slow_computer":
        task = SlowComputerInvestigation().run()
        try:
            explanation = InvestigationInterpreter(OllamaProvider()).explain(task)
        except ModelUnavailable:
            explanation = {"interpretation": task.result["summary"], "next_step": task.result["recommended_next_step"], "evidence": task.findings, "grounded": False}
        evidence = {"task": task.to_dict(), "explanation": explanation}
    elif intent == "diagnose_startup_applications":
        data, findings = ApplicationsDiagnostic().analyze()
        evidence = {"data": data, "findings": [finding.to_dict() for finding in findings]}
    elif intent == "investigate_application_crash":
        application = _application_from_request(request)
        if not application:
            evidence = {"needs_application_name": True, "message": "Which application should I investigate? For example, say: Chrome keeps crashing."}
        else:
            evidence = {"task": ApplicationCrashInvestigation().run(application).to_dict(), "application": application}
    elif intent == "inspect_downloads":
        evidence = {"inspection": DirectoryInspector().inspect(Path.home() / "Downloads")}
    elif intent == "inspect_user_folders":
        evidence = {"inspection": DirectoryInspector().inspect(Path.home())}
    elif intent == "review_downloads_proposals":
        proposals = [proposal.to_dict() for proposal in CleanupProposalPlanner().for_downloads()]
        PermissionLedger().save_proposals(proposals)
        evidence = {"proposals": proposals, "execution": "disabled"}
    else:
        evidence = {
            "message": "I am not sure which safe follow-up fits that request. Do you want system performance, startup applications, storage and Downloads, or the current system status? Moon can only continue with an allowed read-only investigation or a review-only proposal.",
            "execution": "disabled",
        }
    store.add_event(task_id, "follow_up_completed", {"request": request, "classified_intent": intent, "evidence": evidence})
    return {"task_id": task_id, "follow_up": request, "intent": intent, "result": evidence, "conversation": conversation}


@app.get("/tasks")
def recent_tasks() -> dict:
    return {"tasks": TaskStore().list_recent()}


@app.get("/tasks/{task_id}")
def get_task(task_id: str) -> dict:
    try:
        return TaskStore().get(task_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/monitor/check")
def monitor_check() -> dict:
    return Monitor().check()


@app.get("/monitor/history")
def monitor_history() -> dict:
    return {"snapshots": MonitorStore().list_recent()}


@app.get("/monitor/settings")
def monitor_settings() -> dict:
    return MonitorStore().settings()


@app.post("/monitor/settings")
def update_monitor_settings(body: MonitoringConfig) -> dict:
    if not 5 <= body.interval_minutes <= 1440:
        raise HTTPException(status_code=400, detail="Monitoring interval must be between 5 minutes and 24 hours.")
    settings = MonitorStore().update_settings(body.enabled, body.interval_minutes)
    _monitor_wake.set()
    return settings


@app.get("/monitor/events")
def monitor_events() -> dict:
    return {"events": MonitorStore().list_events()}


@app.get("/downloads/inspection")
def inspect_downloads() -> dict:
    from pathlib import Path
    return DirectoryInspector().inspect(Path.home() / "Downloads")


@app.get("/folders/inspection")
def inspect_user_folders() -> dict:
    return DirectoryInspector().inspect(Path.home())


@app.get("/proposals/downloads")
def downloads_proposals() -> dict:
    proposals = [proposal.to_dict() for proposal in CleanupProposalPlanner().for_downloads()]
    PermissionLedger().save_proposals(proposals)
    return {"proposals": proposals, "execution": "disabled"}


@app.post("/proposals/{proposal_id}/preview")
def preview_proposal(proposal_id: str, body: MovePreview) -> dict:
    _require_local_actions_enabled()
    try:
        return ControlledMove().preview(proposal_id, body.destination)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/proposals/{proposal_id}/approve")
def approve_proposal(proposal_id: str, body: MoveApproval) -> dict:
    _require_local_actions_enabled()
    if not body.confirmed:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required before approving a move.")
    try:
        # Validate immediately before recording approval so stale proposals cannot be approved.
        preview = ControlledMove().preview(proposal_id, body.destination)
        PermissionLedger().approve_move(proposal_id, body.destination)
        return {"proposal_id": proposal_id, "state": "approved", "preview": preview, "message": "The move is approved locally but has not been executed."}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/proposals/{proposal_id}/execute")
def execute_proposal(proposal_id: str) -> dict:
    _require_local_actions_enabled()
    try:
        result = ControlledMove().execute(proposal_id)
        return {"proposal_id": proposal_id, "state": "executed", "result": result}
    except (ValueError, RuntimeError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/proposals/{proposal_id}/copy/preview")
def preview_copy_proposal(proposal_id: str, body: MovePreview) -> dict:
    _require_local_actions_enabled()
    try:
        return ControlledCopy().preview(proposal_id, body.destination)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/proposals/{proposal_id}/copy/approve")
def approve_copy_proposal(proposal_id: str, body: MoveApproval) -> dict:
    _require_local_actions_enabled()
    if not body.confirmed:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required before approving a copy.")
    try:
        preview = ControlledCopy().preview(proposal_id, body.destination)
        PermissionLedger().approve_copy(proposal_id, body.destination)
        return {"proposal_id": proposal_id, "state": "approved", "preview": preview, "message": "The copy is approved locally but has not been executed."}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/proposals/{proposal_id}/copy/execute")
def execute_copy_proposal(proposal_id: str) -> dict:
    _require_local_actions_enabled()
    try:
        result = ControlledCopy().execute(proposal_id)
        return {"proposal_id": proposal_id, "state": "executed", "result": result}
    except (ValueError, RuntimeError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
