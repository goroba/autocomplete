from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator


class ClickBuffer(ABC):
    @abstractmethod
    def click(self, text: str, *, clicks: int = 1) -> None:
        ...

    @abstractmethod
    def click_to_score(self, clicks: int) -> float:
        ...

    @abstractmethod
    def flush(self) -> Iterator[tuple[str, float]]:
        ...

    @abstractmethod
    def __iter__(self) -> Iterator[tuple[str, float]]:
        ...
