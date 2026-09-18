from __future__ import annotations

import argparse
import json

from dera.diagnostics.performance import PerformanceDiagnostic
from dera.diagnostics.storage import StorageDiagnostic
from dera.system.observer import SystemObserver
from dera.system.directory_inspector import DirectoryInspector
from dera.tasks.slow_computer import SlowComputerInvestigation
from dera.tasks.cleanup_proposals import CleanupProposalPlanner
from dera.permissions.ledger import PermissionLedger
from dera.tools.controlled_move import ControlledMove
from dera.models.ollama import OllamaProvider
from dera.models.interpreter import InvestigationInterpreter
from dera.models.provider import ModelUnavailable
from dera.tasks.router import IntentRouter
from dera.memory.task_store import TaskStore
from dera.diagnostics.applications import ApplicationsDiagnostic
from dera.system.windows_apps import WindowsApplicationsObserver
from dera.tasks.startup_proposals import StartupProposalPlanner
from dera.tasks.application_crash import ApplicationCrashInvestigation
from dera.diagnostics.hardware import HardwareDiagnostic
from dera.diagnostics.monitor import Monitor
from dera.interface.presenter import proposals_report, task_list, task_report
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Moon — Dera1.4 local system observer")
    parser.add_argument("command", choices=["status", "diagnose", "inspect", "inspect-startup", "investigate", "propose", "approve", "preview", "execute", "dismiss", "explain-slow", "ask", "tasks", "task", "continue-task", "monitor"])
    parser.add_argument("target", nargs="?")
    parser.add_argument("destination", nargs="?")
    parser.add_argument("message", nargs="*")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--debug", action="store_true", help="Include local model validation details")
    args = parser.parse_args()
    if args.command == "monitor":
        if args.target != "check":
            parser.error("monitor requires the target: check")
        result: object = Monitor().check()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("MOON — Monitor check\n")
            for finding in result["findings"]:
                print(f"! {finding['message']}")
            if not result["findings"]:
                print("✓ No meaningful change detected.")
        return
    if args.command == "inspect-startup":
        if not args.target:
            parser.error("inspect-startup requires an entry name")
        try:
            result: object = WindowsApplicationsObserver().inspect_startup_entry(args.target)
        except ValueError as error:
            parser.error(str(error))
        print(json.dumps(result, indent=2 if args.json else None))
        return
    if args.command == "tasks":
        tasks = TaskStore().list_recent()
        print(json.dumps({"tasks": tasks}, indent=2) if args.json else task_list(tasks))
        return
    if args.command == "task":
        if not args.target:
            parser.error("task requires a task ID")
        try:
            result: object = TaskStore().get(args.target)
        except ValueError as error:
            parser.error(str(error))
        print(json.dumps(result, indent=2) if args.json else task_report(result))
        return
    if args.command == "continue-task":
        if not args.target:
            parser.error("continue-task requires a task ID and a follow-up request")
        follow_up = " ".join(part for part in [args.destination, *args.message] if part)
        if not follow_up:
            parser.error("continue-task requires a follow-up request in quotes")
        try:
            intent = IntentRouter(OllamaProvider()).route(follow_up)
            if intent == "inspect_downloads":
                evidence: object = DirectoryInspector().inspect(Path.home() / "Downloads")
            elif intent == "system_status":
                evidence = SystemObserver().snapshot()
            elif intent == "review_downloads_proposals":
                proposals = [proposal.to_dict() for proposal in CleanupProposalPlanner().for_downloads()]
                PermissionLedger().save_proposals(proposals)
                evidence = {"proposals": proposals, "execution": "disabled"}
            elif intent == "investigate_slow_computer":
                evidence = SlowComputerInvestigation().run().to_dict()
            elif intent == "explain_slow_computer":
                investigation = SlowComputerInvestigation().run()
                evidence = {"task_id": investigation.id, "explanation": InvestigationInterpreter(OllamaProvider()).explain(investigation)}
            elif intent == "diagnose_startup_applications":
                data, findings = ApplicationsDiagnostic().analyze()
                evidence = {"data": data, "findings": [finding.to_dict() for finding in findings]}
            else:
                evidence = {"message": "This request is outside Moon's current safe task allow-list."}
            TaskStore().add_event(args.target, "follow_up_completed", {"request": follow_up, "classified_intent": intent, "evidence": evidence})
            result = {"task_id": args.target, "follow_up": follow_up, "classified_intent": intent, "state": "completed", "evidence": evidence}
        except (ValueError, ModelUnavailable) as error:
            parser.error(str(error))
        print(json.dumps(result, indent=2 if args.json else None))
        return
    if args.command == "ask":
        request = " ".join(part for part in [args.target, args.destination, *args.message] if part)
        if not request:
            parser.error("ask requires a request in quotes")
        try:
            intent = IntentRouter(OllamaProvider()).route(request)
        except ModelUnavailable as error:
            parser.error(str(error))
        if intent == "system_status":
            result: object = SystemObserver().snapshot()
        elif intent == "investigate_slow_computer":
            task = SlowComputerInvestigation().run()
            result = {"task": task.to_dict(), "explanation": InvestigationInterpreter(OllamaProvider()).explain(task)}
        elif intent == "inspect_downloads":
            result = DirectoryInspector().inspect(Path.home() / "Downloads")
        elif intent == "review_downloads_proposals":
            proposals = [proposal.to_dict() for proposal in CleanupProposalPlanner().for_downloads()]
            PermissionLedger().save_proposals(proposals)
            result = {"proposals": proposals, "execution": "disabled"}
        elif intent == "explain_slow_computer":
            task = SlowComputerInvestigation().run()
            result = {"task_id": task.id, "explanation": InvestigationInterpreter(OllamaProvider()).explain(task)}
        elif intent == "diagnose_startup_applications":
            data, findings = ApplicationsDiagnostic().analyze()
            result = {"data": data, "findings": [finding.to_dict() for finding in findings]}
        else:
            result = {"message": "I can currently check system status, investigate slowness, inspect Downloads, review cleanup proposals, or explain a slow-computer investigation.", "intent": "unknown"}
        print(json.dumps({"request": request, "intent": intent, "result": result}, indent=2 if args.json else None))
        return
    if args.command == "explain-slow":
        task = SlowComputerInvestigation().run()
        try:
            explanation = InvestigationInterpreter(OllamaProvider()).explain(task)
        except ModelUnavailable as error:
            parser.error(str(error))
        if not args.debug:
            explanation.pop("validation_error", None)
            explanation.pop("raw_model_response", None)
        output = {"task_id": task.id, "model": OllamaProvider().model, "explanation": explanation}
        print(json.dumps(output, indent=2) if args.json else task_report(task.to_dict()) + "\n\nMoon's interpretation\n" + explanation["interpretation"])
        return
    if args.command == "dismiss":
        if not args.target:
            parser.error("dismiss requires a proposal ID")
        try:
            PermissionLedger().dismiss(args.target)
        except ValueError as error:
            parser.error(str(error))
        print(json.dumps({"proposal_id": args.target, "state": "dismissed", "message": "The proposal was removed from Moon's local queue. No files were changed."}, indent=2 if args.json else None))
        return
    if args.command == "propose":
        if args.target == "startup":
            result: object = {"objective": "Review optional startup applications", "proposals": StartupProposalPlanner().proposals(), "execution": "not implemented"}
            print(json.dumps(result, indent=2) if args.json else proposals_report(result["proposals"]))
            return
        if args.target != "cleanup-downloads":
            parser.error("propose requires the target: cleanup-downloads or startup")
        proposals = [proposal.to_dict() for proposal in CleanupProposalPlanner().for_downloads()]
        PermissionLedger().save_proposals(proposals)
        result: object = {"objective": "Propose cleanup candidates for Downloads", "proposals": proposals, "execution": "disabled", "message": "No files were moved or deleted. Each proposal requires explicit confirmation before a future action tool may run."}
        print(json.dumps(result, indent=2) if args.json else proposals_report(proposals))
        return
    if args.command == "approve":
        if not args.target or not args.destination:
            parser.error("approve requires a proposal ID and a destination directory")
        try:
            PermissionLedger().approve_move(args.target, args.destination)
        except ValueError as error:
            parser.error(f"{error} Run 'python main.py propose cleanup-downloads --json' and use an ID from its proposals list.")
        print(json.dumps({"proposal_id": args.target, "action": "move", "state": "approved", "execution": "still requires a separate execute command"}, indent=2 if args.json else None))
        return
    if args.command == "execute":
        if not args.target:
            parser.error("execute requires an approved proposal ID")
        try:
            result = ControlledMove().execute(args.target)
        except (ValueError, RuntimeError) as error:
            parser.error(str(error))
        print(json.dumps(result, indent=2) if args.json else f"MOON — Move verified\n✓ {result['source']}\n→ {result['destination']}\nFree-space change: {result['free_space_change_gb']} GB")
        return
    if args.command == "preview":
        if not args.target or not args.destination:
            parser.error("preview requires a proposal ID and a destination directory")
        try:
            result = ControlledMove().preview(args.target, args.destination)
        except ValueError as error:
            parser.error(str(error))
        print(json.dumps(result, indent=2 if args.json else None))
        return
    if args.command == "diagnose" and args.target not in {"performance", "storage", "applications", "hardware"}:
        parser.error("diagnose requires the target: performance, storage, applications, or hardware")
    if args.command == "inspect":
        if not args.target:
            parser.error("inspect requires a directory path")
        result: object = DirectoryInspector().inspect(args.target)
        print(json.dumps(result, indent=2 if args.json else None))
        return
    if args.command == "investigate":
        if args.target == "slow-computer":
            result: object = SlowComputerInvestigation().run().to_dict()
        elif args.target == "crash" and args.destination:
            try:
                result = ApplicationCrashInvestigation().run(args.destination).to_dict()
            except (ValueError, RuntimeError) as error:
                parser.error(str(error))
        else:
            parser.error("investigate requires: slow-computer, or crash APPLICATION_NAME")
        print(json.dumps(result, indent=2 if args.json else None))
        return
    snapshot = SystemObserver().snapshot()
    if args.command == "status":
        result: object = snapshot
    elif args.target == "storage":
        result = {"snapshot": {"storage": snapshot["storage"]}, "findings": [finding.to_dict() for finding in StorageDiagnostic().analyze_user_directories()]}
    elif args.target == "applications":
        data, findings = ApplicationsDiagnostic().analyze()
        result = {"data": data, "findings": [finding.to_dict() for finding in findings]}
    elif args.target == "hardware":
        data, findings = HardwareDiagnostic().analyze()
        result = {"data": data, "findings": [finding.to_dict() for finding in findings]}
    else:
        result = {"snapshot": snapshot, "findings": [finding.to_dict() for finding in PerformanceDiagnostic().analyze(snapshot)]}
    print(json.dumps(result, indent=2 if args.json else None))
