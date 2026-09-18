from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

Severity = Literal["info", "warning", "critical"]


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    title: str
    evidence: dict[str, Any]
    recommendation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
