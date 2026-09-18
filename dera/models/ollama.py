from __future__ import annotations

import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen

from dera.models.provider import ModelProvider, ModelUnavailable


class OllamaProvider(ModelProvider):
    """Local Ollama adapter; model choice can be changed without touching Dera1.4."""

    def __init__(self, model: str | None = None, base_url: str = "http://127.0.0.1:11434") -> None:
        self.model = model or os.getenv("MOON_MODEL", "llama3.1:8b")
        self.base_url = base_url.rstrip("/")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        payload = json.dumps({"model": self.model, "stream": False, "format": "json", "options": {"temperature": 0}, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]}).encode()
        request = Request(f"{self.base_url}/api/chat", data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=120) as response:
                body = json.loads(response.read())
        except URLError as error:
            raise ModelUnavailable("Ollama is not reachable. Start Ollama and install the configured 8B model before using explain-slow.") from error
        if "error" in body:
            raise ModelUnavailable(f"Ollama could not use {self.model}: {body['error']}")
        return body["message"]["content"].strip()

    def status(self) -> dict:
        """Read-only availability check for the local settings view."""
        request = Request(f"{self.base_url}/api/tags", method="GET")
        try:
            with urlopen(request, timeout=3) as response:
                body = json.loads(response.read())
        except (URLError, TimeoutError, json.JSONDecodeError):
            return {"reachable": False, "model": self.model, "base_url": self.base_url, "installed": False}
        installed = any(item.get("name") == self.model for item in body.get("models", []))
        return {"reachable": True, "model": self.model, "base_url": self.base_url, "installed": installed}
