from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Engine(ABC):
    @abstractmethod
    def store(self, text: str, *, score: float | None = None, metadata: dict[str, Any] | None = None) -> None:
        ...

    @abstractmethod
    def search(self, query: str) -> list[tuple[str, float, dict[str, Any]]]:
        ...

    @abstractmethod
    def click(self, text: str, *, clicks: int = 1) -> None:
        ...

    @abstractmethod
    def rescore(self, text: str, delta_score: float) -> None:
        ...

    @abstractmethod
    def flush(self) -> None:
        ...

    @abstractmethod
    def delete(self, text: str) -> None:
        ...
