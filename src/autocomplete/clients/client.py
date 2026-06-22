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
        min_query_length: int = 1,
    ) -> None:
        self.normalizer = normalizer
        self.tokenizer = tokenizer
        self.top_n = top_n
        self.min_query_length = min_query_length

    @abstractmethod
    def store(self, text: str, *, score: float | None = None, metadata: dict[str, Any] | None = None) -> None:
        ...

    @abstractmethod
    def search(self, query: str) -> list[tuple[str, float, dict[str, Any]]]:
        ...

    @abstractmethod
    def click(self, text: str, *, amount: int | None = None) -> None:
        ...

    @abstractmethod
    def delete(self, text: str) -> None:
        ...
