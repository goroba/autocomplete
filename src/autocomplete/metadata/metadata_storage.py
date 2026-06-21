from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MetadataStorage(ABC):
    @abstractmethod
    def get(self, key: str) -> dict[str, Any] | None:
        ...

    @abstractmethod
    def set(self, key: str, metadata: dict[str, Any]) -> None:
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        ...
