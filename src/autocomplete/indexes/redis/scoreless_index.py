from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autocomplete.indexes import Index
from autocomplete.metadata import MetadataStorage, NullMetadataStorage
from autocomplete.normalizers import Normalizer

if TYPE_CHECKING:
    from redis import Redis


class ScorelessIndex(Index):
    def __init__(
        self,
        name: str,
        redis: Redis,
        *,
        top_n: int = 5,
        normalizer: Normalizer,
        metadata_storage: MetadataStorage | None = None,
    ) -> None:
        self.name = name
        self.redis = redis
        self.top_n = top_n
        self.normalizer = normalizer
        self.metadata_storage = metadata_storage or NullMetadataStorage()
        self.trie_key = f"{self.name}:trie"

    def store(self, text: str, *, score: float | None = None, metadata: dict[str, Any] | None = None) -> None:
        normalized_text = self.normalizer.normalize(text)
        self.redis.zadd(self.trie_key, {normalized_text: 0})

        if metadata is not None:
            self.metadata_storage.set(normalized_text, metadata)

    def search(self, query: str) -> list[tuple[str, float, dict[str, Any]]]:
        normalized_query = self.normalizer.normalize(query)
        if not normalized_query:
            return []

        results: list[str] = self.redis.zrange(
            self.trie_key,
            f"[{normalized_query}",
            f"[{normalized_query}\xff",
            bylex=True,
            offset=0,
            num=self.top_n,
        )

        return [
            (text, 0.0, self.metadata_storage.get(text) or {})
            for text in results[: self.top_n]
        ]

    def click(self, text: str, *, clicks: int = 1) -> None:
        pass

    def rescore(self, text: str, delta_score: float) -> None:
        pass

    def flush(self) -> None:
        pass

    def delete(self, text: str) -> None:
        normalized_text = self.normalizer.normalize(text)
        self.redis.zrem(self.trie_key, normalized_text)
        self.metadata_storage.delete(normalized_text)
