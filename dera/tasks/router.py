from __future__ import annotations

import json

from dera.models.provider import ModelProvider


class IntentRouter:
    """Turns natural language into a small, validated Dera1.4 task allow-list."""

    ALLOWED_INTENTS = {
        "system_status",
        "investigate_slow_computer",
        "inspect_downloads",
        "review_downloads_proposals",
        "explain_slow_computer",
        "diagnose_startup_applications",
        "investigate_application_crash",
        "unknown",
    }
    PROMPT = "Classify the user request. Return JSON only: {\"intent\": one allowed intent}. Allowed intents: system_status, investigate_slow_computer, inspect_downloads, review_downloads_proposals, explain_slow_computer, diagnose_startup_applications, investigate_application_crash, unknown. Do not include tools, paths, arguments, actions, or explanations."

    def __init__(self, provider: ModelProvider) -> None:
        self.provider = provider

    def route(self, request: str) -> str:
        deterministic = self._fallback(request)
        if deterministic != "unknown":
            return deterministic
        try:
            response = json.loads(self.provider.generate(self.PROMPT, request))
            intent = response.get("intent")
            return intent if intent in self.ALLOWED_INTENTS else "unknown"
        except (json.JSONDecodeError, TypeError, ValueError):
            return self._fallback(request)

    @staticmethod
    def _fallback(request: str) -> str:
        text = request.lower()
        startup_terms = ("startup", "start up", "boot", "booting", "launch at login", "launches at login", "open on startup", "start when i", "takes forever to start", "slow to start", "slow boot")
        crash_terms = ("crash", "crashes", "crashing", "keeps closing", "kept closing", "closed unexpectedly", "stopped working", "app closed")
        slow_terms = ("slow", "sluggish", "lag", "laggy", "stutter", "freez", "unresponsive", "performance", "takes forever", "hanging", "hangs", "running badly")
        explain_terms = ("explain", "what does this mean", "simpler", "break this down", "help me understand", "tell me more")
        proposal_terms = ("clean up", "cleanup", "free space", "clear space", "make space", "move files", "move folders", "what can i remove", "what can i move")
        downloads_terms = ("downloads", "download folder", "downloaded files", "large files")
        status_terms = ("system status", "computer status", "what is using my ram", "what's using my ram", "what is eating memory", "what's eating memory", "memory", "ram", "cpu", "processor", "battery", "network", "disk space", "storage")
        if any(term in text for term in startup_terms):
            return "diagnose_startup_applications"
        if any(term in text for term in crash_terms):
            return "investigate_application_crash"
        if any(term in text for term in explain_terms) and any(term in text for term in ("slow", "performance", "computer", "system", "finding", "result")):
            return "explain_slow_computer"
        if any(term in text for term in proposal_terms) and (any(term in text for term in downloads_terms) or "space" in text):
            return "review_downloads_proposals"
        if any(term in text for term in slow_terms):
            return "investigate_slow_computer"
        if any(term in text for term in downloads_terms):
            return "inspect_downloads"
        if any(term in text for term in status_terms):
            return "system_status"
        return "unknown"
