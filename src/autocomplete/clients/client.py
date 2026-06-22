from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from autocomplete.normalizers.normalizer import Normalizer
from autocomplete.tokenizers.tokenizer import Tokenizer


class Client(ABC):
    def __init__(
        self,
        *,
        normalizer: Normalizer,
        tokenizer: Tokenizer,
        top_n: int = 5,
    ) -> None:
        self.normalizer = normalizer
        self.tokenizer = tokenizer
        self.top_n = top_n

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
    def rescore(self, text: str, score: float) -> None:
        ...

    @abstractmethod
    def delete(self, text: str) -> None:
        ...

    @abstractmethod
    def flush(self) -> None:
        ...
