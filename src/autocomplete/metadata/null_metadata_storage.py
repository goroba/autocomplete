from __future__ import annotations

from typing import Any

from autocomplete.metadata.metadata_storage import MetadataStorage


class NullMetadataStorage(MetadataStorage):
    def get(self, key: str) -> dict[str, Any] | None:
        return None

    def set(self, key: str, metadata: dict[str, Any]) -> None:
        pass

    def delete(self, key: str) -> None:
        pass
