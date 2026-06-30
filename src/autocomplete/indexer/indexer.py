from __future__ import annotations

from abc import ABC, abstractmethod

from autocomplete.indexes import Index


class Indexer(ABC):
    @abstractmethod
    def populate(self, index: Index) -> int:
        ...
