from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

RiskLevel = Literal["read_only", "controlled", "privileged"]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    risk_level: RiskLevel
    confirmation_required: bool
    timeout_seconds: int
    handler: Callable[..., Any]


class ToolRegistry:
    """The explicit allow-list for all Dera1.4 capabilities."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc
