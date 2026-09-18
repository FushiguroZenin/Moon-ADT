from __future__ import annotations

import json
import re

from dera.models.provider import ModelProvider
from dera.tasks.task import Task


class InvestigationInterpreter:
    """Lets the model explain evidence; it cannot execute tools or approve actions."""

    SYSTEM_PROMPT = "You format a read-only computer health report. Return a JSON object only: {\"summary\": string, \"finding_ids\": [string], \"next_step\": string}. Select finding_ids only from the report. Do not include digits in summary or next_step. Do not add facts or instructions outside the report."

    def __init__(self, provider: ModelProvider) -> None:
        self.provider = provider

    def explain(self, task: Task) -> dict:
        evidence = {"objective": task.objective, "findings": task.findings, "result": task.result}
        raw = self.provider.generate(self.SYSTEM_PROMPT, "Format this diagnostic report:\n" + json.dumps(evidence))
        allowed = {finding["code"]: finding for finding in task.findings}
        try:
            start, end = raw.find("{"), raw.rfind("}")
            if start < 0 or end < start:
                raise ValueError("No JSON object was found in the model response.")
            response = json.loads(raw[start : end + 1])
            selected = [allowed[code] for code in response["finding_ids"] if code in allowed]
            if not selected or re.search(r"\d", response["summary"] + response["next_step"]):
                raise ValueError("The response contained unsupported IDs or numeric claims.")
            return {"interpretation": response["summary"], "next_step": response["next_step"], "evidence": selected, "grounded": True}
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            selected = [finding for finding in task.findings if finding["severity"] in {"warning", "critical"}]
            return {"interpretation": "Dera1.4 found conditions that need review.", "next_step": task.result["recommended_next_step"], "evidence": selected, "grounded": False, "validation_error": str(error), "raw_model_response": raw}
