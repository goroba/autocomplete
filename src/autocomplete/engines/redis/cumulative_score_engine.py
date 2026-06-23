from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from autocomplete.click_buffers import ClickBuffer, NoopClickBuffer
from autocomplete.engines import Engine
from autocomplete.metadata import MetadataStorage, NullMetadataStorage
from autocomplete.normalizers import Normalizer
from autocomplete.tokenizers import Tokenizer

if TYPE_CHECKING:
    from redis import Redis


class CumulativeScoreEngine(Engine):
    def __init__(
        self,
        name: str,
        redis: Redis,
        *,
        top_n: int = 5,
        normalizer: Normalizer,
        tokenizer: Tokenizer,
        metadata_storage: MetadataStorage | None = None,
        click_buffer: ClickBuffer | None = None,
    ) -> None:
        self.normalizer = normalizer
        self.tokenizer = tokenizer
        self.top_n = top_n
        self.name = name
        self.redis = redis
        self.metadata_storage = metadata_storage or NullMetadataStorage()
        self.click_buffer = click_buffer or NoopClickBuffer()
        self.click_buffer.set_engine(self)

    def _prefix_key(self, token_prefix: str) -> str:
        return f"{self.name}:prefix:{token_prefix}"

    def _iter_prefix_keys(self, normalized_text: str) -> Iterator[str]:
        for token in self.tokenizer.tokenize(normalized_text):
            for i in range(1, len(token) + 1):
                yield self._prefix_key(token[:i])

    def store(self, text: str, *, score: float | None = None, metadata: dict[str, Any] | None = None) -> None:
        member_score = score if score is not None else 0
        normalized_text = self.normalizer.normalize(text)

        for key in self._iter_prefix_keys(normalized_text):
            self.redis.zadd(key, {text: member_score})
            self.redis.zremrangebyrank(key, 0, -(self.top_n + 1))

        if metadata is not None:
            self.metadata_storage.set(normalized_text, metadata)

    def search(self, query: str) -> list[tuple[str, float, dict[str, Any]]]:
        normalized_query = self.normalizer.normalize(query)
        tokens = self.tokenizer.tokenize(normalized_query)
        if not tokens:
            return []

        if len(tokens) == 1:
            results: list[tuple[str, float]] = self.redis.zrevrange(
                self._prefix_key(tokens[0]),
                0,
                self.top_n - 1,
                withscores=True,
            )
        else:
            temp_key = f"{self.name}:search:{uuid4()}"
            prefix_keys = [self._prefix_key(token) for token in tokens]
            self.redis.zinterstore(temp_key, prefix_keys, aggregate="MAX")
            results = self.redis.zrevrange(
                temp_key,
                0,
                self.top_n - 1,
                withscores=True,
            )
            self.redis.delete(temp_key)

        return [
            (text, score, self.metadata_storage.get(self.normalizer.normalize(text)) or {})
            for text, score in results
        ]

    def click(self, text: str, *, clicks: int = 1) -> None:
        self.click_buffer.click(text, clicks=clicks)

    def rescore(self, text: str, score: float) -> None:
        normalized_text = self.normalizer.normalize(text)
        for key in self._iter_prefix_keys(normalized_text):
            self.redis.zincrby(key, score, text)
            self.redis.zremrangebyrank(key, 0, -(self.top_n + 1))

    def flush(self) -> None:
        pipe = self.redis.pipeline()
        for text, score in self.click_buffer.flush():
            normalized_text = self.normalizer.normalize(text)
            for key in self._iter_prefix_keys(normalized_text):
                pipe.zincrby(key, score, text)
                pipe.zremrangebyrank(key, 0, -(self.top_n + 1))
        pipe.execute()

    def delete(self, text: str) -> None:
        normalized_text = self.normalizer.normalize(text)
        for key in self._iter_prefix_keys(normalized_text):
            self.redis.zrem(key, text)
        self.metadata_storage.delete(normalized_text)
