from __future__ import annotations

import json
import re

from dera.models.provider import ModelProvider
from dera.tasks.task import Task


class GroundedConversation:
    """Uses a local model for tone, while Dera1.4 retains evidence and control."""

    SYSTEM_PROMPT = (
        "You are Moon, a private computer assistant. Return JSON only with "
        '{"reply": string, "finding_ids": [string], "next_step": string}. '
        "Use only the supplied report. Select finding_ids only from the report. "
        "Do not use digits, measurements, file paths, or facts not present in the report. "
        "Do not claim an action was taken. If a next step could change the computer, "
        "say Moon needs the user's explicit permission before carrying it out. "
        "Keep reply and next_step concise and helpful."
    )

    def __init__(self, provider: ModelProvider) -> None:
        self.provider = provider

    def respond(self, user_request: str, task: Task) -> dict:
        report = {
            "request": user_request,
            "objective": task.objective,
            "findings": task.findings,
            "recommended_next_step": task.result.get("recommended_next_step", ""),
        }
        raw = self.provider.generate(self.SYSTEM_PROMPT, json.dumps(report))
        allowed = {finding["code"]: finding for finding in task.findings}
        try:
            start, end = raw.find("{"), raw.rfind("}")
            if start < 0 or end < start:
                raise ValueError("No JSON object was found in the model response.")
            response = json.loads(raw[start : end + 1])
            reply = response["reply"].strip()
            next_step = response["next_step"].strip()
            ids = response["finding_ids"]
            if not isinstance(ids, list) or re.search(r"\d", reply + next_step):
                raise ValueError("The response contains unsupported numeric claims.")
            selected = [allowed[code] for code in ids if code in allowed]
            if len(selected) != len(ids):
                raise ValueError("The response selected unsupported findings.")
            return {
                "reply": reply,
                "next_step": next_step,
                "evidence": selected,
                "grounded": True,
            }
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            return {
                "reply": task.result.get("summary", "Dera1.4 completed a read-only investigation."),
                "next_step": task.result.get("recommended_next_step", ""),
                "evidence": task.findings,
                "grounded": False,
                "validation_error": str(error),
            }
