from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from autocomplete.clients.client import Client


class ModulePrototype(ABC):
    """Pre-wired autocomplete module configuration."""

    @property
    @abstractmethod
    def client(self) -> Client:
        ...

    def store(
        self,
        text: str,
        score: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.client.store(text, score=score, metadata=metadata)

    def search(self, query: str) -> list[tuple[str, float, dict[str, Any]]]:
        return self.client.search(query)

    def click(self, text: str) -> None:
        self.client.click(text)

    def delete(self, text: str) -> None:
        self.client.delete(text)
