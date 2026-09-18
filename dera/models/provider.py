from __future__ import annotations

from abc import ABC, abstractmethod


class ModelUnavailable(RuntimeError):
    pass


class ModelProvider(ABC):
    """Replaceable language-model boundary for Dera1.4."""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError
