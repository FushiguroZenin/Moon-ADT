from __future__ import annotations

from typing import Any


def task_report(task: dict[str, Any]) -> str:
    lines = [f"MOON — {task['objective']}", f"Task {task['id']} · {task['state']}", ""]
    for finding in task.get("findings", []):
        symbol = {"critical": "✕", "warning": "!", "info": "✓"}[finding["severity"]]
        evidence = finding.get("evidence", {})
        detail = _detail(evidence)
        lines.append(f"{symbol} {finding['title']}{': ' + detail if detail else ''}")
    result = task.get("result") or {}
    if result.get("recommended_next_step"):
        lines += ["", "Next safe step", result["recommended_next_step"]]
    return "\n".join(lines)


def proposals_report(proposals: list[dict[str, Any]]) -> str:
    lines = ["MOON — Review-only proposals", ""]
    for proposal in proposals:
        label = proposal.get("path") or proposal.get("entry", {}).get("name", "proposal")
        size = proposal.get("reclaimable_gb")
        suffix = f" · {size} GB" if size is not None else ""
        lines.append(f"! {label}{suffix}")
        lines.append(f"  {proposal.get('reason', 'Requires review and confirmation.')}")
    lines.append("\nNo change will occur without a separate approval and execution step.")
    return "\n".join(lines)


def task_list(tasks: list[dict[str, Any]]) -> str:
    lines = ["MOON — Recent tasks", ""]
    lines += [f"{task['id']}  {task['state']}  {task['objective']}" for task in tasks]
    return "\n".join(lines) if tasks else "MOON — No recorded tasks yet."


def _detail(evidence: dict[str, Any]) -> str:
    if "usage_percent" in evidence:
        return f"{evidence['usage_percent']}%"
    if "free_gb" in evidence:
        return f"{evidence['free_gb']} GB free"
    if "count" in evidence:
        return f"{evidence['count']} found"
    return ""
