from __future__ import annotations

from abc import ABC, abstractmethod


class Tokenizer(ABC):
    @abstractmethod
    def tokenize(self, text: str) -> list[str]:
        ...
