from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autocomplete.clients.client import Client
from autocomplete.metadata import MetadataStorage, NullMetadataStorage
from autocomplete.normalizers.normalizer import Normalizer
from autocomplete.tokenizers.noop_tokenizer import NoopTokenizer

if TYPE_CHECKING:
    from redis import Redis


class ScorelessClient(Client):
    def __init__(
        self,
        name: str,
        redis: Redis,
        *,
        normalizer: Normalizer,
        top_n: int = 5,
        metadata_storage: MetadataStorage | None = None,
    ) -> None:
        super().__init__(
            normalizer=normalizer,
            tokenizer=NoopTokenizer(),
            top_n=top_n,
        )
        self.name = name
        self.redis = redis
        self.metadata_storage = metadata_storage or NullMetadataStorage()

    def _trie_key(self) -> str:
        return f"{self.name}:trie"

    def store(self, text: str, *, score: float | None = None, metadata: dict[str, Any] | None = None) -> None:
        normalized_text = self.normalizer.normalize(text)
        self.redis.zadd(self._trie_key(), {normalized_text: 0})

        if metadata is not None:
            self.metadata_storage.set(normalized_text, metadata)

    def search(self, query: str) -> list[tuple[str, float, dict[str, Any]]]:
        normalized_query = self.normalizer.normalize(query)
        if not normalized_query:
            return []

        results: list[tuple[str, float]] = self.redis.zrange(
            self._trie_key(),
            f"[{normalized_query}",
            f"[{normalized_query}\xff",
            bylex=True,
            offset=0,
            num=self.top_n,
            withscores=True,
        )

        return [
            (text, score, self.metadata_storage.get(text) or {})
            for text, score in results[: self.top_n]
        ]

    def click(self, text: str, *, clicks: int = 1) -> None:
        pass

    def rescore(self, text: str, score: float) -> None:
        pass

    def delete(self, text: str) -> None:
        normalized_text = self.normalizer.normalize(text)
        self.redis.zrem(self._trie_key(), normalized_text)
        self.metadata_storage.delete(normalized_text)

    def flush(self) -> None:
        pass
