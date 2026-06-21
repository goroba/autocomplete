from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autocomplete.clients.client import Client
from autocomplete.metadata.metadata_storage import MetadataStorage
from autocomplete.metadata.redis.redis_metadata_storage import RedisMetadataStorage
from autocomplete.normalizers.normalizer import Normalizer
from autocomplete.tokenizers.tokenizer import Tokenizer

if TYPE_CHECKING:
    from redis import Redis


class SimpleTrieClient(Client):
    def __init__(
        self,
        prefix: str,
        redis: Redis,
        *,
        normalizer: Normalizer,
        tokenizer: Tokenizer,
        top_n: int = 5,
        scoreable: bool = True,
        metadata_storage: MetadataStorage | None = None,
    ) -> None:
        super().__init__(normalizer=normalizer, tokenizer=tokenizer, top_n=top_n)
        self.prefix = prefix
        self.redis = redis
        self.scoreable = scoreable
        self.metadata_storage = metadata_storage

    def _iterate_keys(self, text: str) -> str:
        for token in self.tokenizer.tokenize(text):
            normalized = self.normalizer.normalize(token)
            yield f"{self.prefix}:prefix:{normalized}"

    def store(
        self,
        text: str,
        score: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if metadata is not None and not self.metadata_storage:
            raise ValueError("`metadata` can only be passed when `metadata_storage` is defined")

        value_score = score if score is not None else 0.0

        for key in self._iterate_keys(text):
            self.redis.zadd(key, {text: value_score})

        if metadata is not None:
            self.metadata_storage.set(text, metadata)

    def search(self, query: str) -> list[tuple[str, float, dict[str, Any]]]:
        results: list[tuple[str, float]] = []
        for key in self._iterate_keys(query):
            results.extend(
                self.redis.zrevrange(key, 0, self.top_n - 1, withscores=True)
            )
        results.sort(key=lambda item: item[1], reverse=True)

        output: list[tuple[str, float, dict[str, Any]]] = []
        for text, score in results[: self.top_n]:
            metadata = self.metadata_storage.get(text) if self.metadata_storage else None
            output.append((text, score, metadata or {}))
        return output

    def click(self, text: str) -> None:
        for key in self._iterate_keys(text):
            self.redis.zincrby(key, 1, text)

    def delete(self, text: str) -> None:
        for key in self._iterate_keys(text):
            self.redis.zrem(key, text)
        if self.metadata_storage:
            self.metadata_storage.delete(text)