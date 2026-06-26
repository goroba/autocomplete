from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from autocomplete.click_buffers import ClickBuffer, NoopClickBuffer
from autocomplete.engines import Engine
from autocomplete.metadata import MetadataStorage, NullMetadataStorage
from autocomplete.normalizers import Normalizer
from autocomplete.tokenizers import Tokenizer

if TYPE_CHECKING:
    from redis import Redis


class BidirectionalScoreEngine(Engine):
    def __init__(
        self,
        name: str,
        redis: Redis,
        *,
        top_n: int = 5,
        trim: bool = True,
        normalizer: Normalizer,
        tokenizer: Tokenizer,
        metadata_storage: MetadataStorage | None = None,
        click_buffer: ClickBuffer | None = None,
    ) -> None:
        self.name = name
        self.redis = redis
        self.top_n = top_n
        self.trim = trim
        self.normalizer = normalizer
        self.tokenizer = tokenizer
        self.metadata_storage = metadata_storage or NullMetadataStorage()
        self.click_buffer = click_buffer or NoopClickBuffer()
        self.vocabulary_key = f"{self.name}:vocabulary"

    def _get_prefix_key(self, prefix: str) -> str:
        return f"{self.name}:prefix:{prefix}"

    def _trim_prefix_set(self, prefix_key: str) -> None:
        if not self.trim:
            return

        self.redis.zremrangebyrank(prefix_key, 0, -(self.top_n + 1))

    def _rebuild_prefix_set(self, prefix: str) -> None:
        if not self.trim:
            return

        prefix_key = self._get_prefix_key(prefix)
        members = self.redis.zrange(
            self.vocabulary_key,
            f"[{prefix}",
            f"[{prefix}\xff",
            bylex=True,
        )
        if not members:
            self.redis.zremrangebyrank(prefix_key, 0, -1)
            return

        scores = self.redis.zmscore(self.vocabulary_key, members)
        members = [
            (name, score)
            for name, score in zip(members, scores)
            if score is not None
        ]
        members.sort(key=lambda x: x[1], reverse=True)
        members = members[: self.top_n]

        with self.redis.pipeline() as pipe:
            pipe.delete(prefix_key)
            pipe.zadd(prefix_key, dict(members))
            pipe.execute()

    def store(self, text: str, *, score: float | None = None, metadata: dict[str, Any] | None = None) -> None:
        member_score = score if score is not None else 0
        normalized_text = self.normalizer.normalize(text)

        self.redis.zadd(self.vocabulary_key, {normalized_text: member_score})
        for token in self.tokenizer.tokenize(normalized_text):
            for i in range(len(token), 0, -1):
                prefix = token[:i]
                prefix_key = self._get_prefix_key(prefix)
                self.redis.zadd(prefix_key, {normalized_text: member_score})
                self._trim_prefix_set(prefix_key)

        if metadata is not None:
            self.metadata_storage.set(normalized_text, metadata)

    def search(self, query: str) -> list[tuple[str, float, dict[str, Any]]]:
        normalized_query = self.normalizer.normalize(query)
        tokens = self.tokenizer.tokenize(normalized_query)
        if not tokens:
            return []

        if len(tokens) == 1:
            results: list[tuple[str, float]] = self.redis.zrevrange(
                self._get_prefix_key(tokens[0]),
                0,
                self.top_n - 1,
                withscores=True,
            )
        else:
            try:
                temp_key = f"{self.name}:search:{uuid4()}"
                prefix_keys = [self._get_prefix_key(token) for token in tokens]
                self.redis.zinterstore(temp_key, prefix_keys, aggregate="MAX")
                results = self.redis.zrevrange(
                    temp_key,
                    0,
                    self.top_n - 1,
                    withscores=True,
                )
            finally:
                self.redis.delete(temp_key)

        return [
            (text, score, self.metadata_storage.get(text) or {})
            for text, score in results
        ]

    def click(self, text: str, *, clicks: int = 1) -> None:
        self.click_buffer.click(text, clicks=clicks)

    def rescore(self, text: str, delta_score: float) -> None:
        normalized_text = self.normalizer.normalize(text)

        self.redis.zincrby(self.vocabulary_key, delta_score, normalized_text)
        score = self.redis.zscore(self.vocabulary_key, normalized_text)
        if score is None:
            return
        for token in self.tokenizer.tokenize(normalized_text):
            for i in range(len(token), 0, -1):
                prefix = token[:i]
                prefix_key = self._get_prefix_key(prefix)
                self.redis.zadd(prefix_key, {normalized_text: score})
                if delta_score < 0:
                    self._rebuild_prefix_set(prefix)
                else:
                    self._trim_prefix_set(prefix_key)

    def flush(self) -> None:
        for text, delta_score in self.click_buffer.flush():
            normalized_text = self.normalizer.normalize(text)
            self.redis.zincrby(self.vocabulary_key, delta_score, normalized_text)
            score = self.redis.zscore(self.vocabulary_key, normalized_text)
            if score is None:
                continue
            for token in self.tokenizer.tokenize(normalized_text):
                for i in range(len(token), 0, -1):
                    prefix = token[:i]
                    prefix_key = self._get_prefix_key(prefix)
                    self.redis.zadd(prefix_key, {normalized_text: score})
                    if delta_score < 0:
                        self._rebuild_prefix_set(prefix)
                    else:
                        self._trim_prefix_set(prefix_key)

    def delete(self, text: str) -> None:
        normalized_text = self.normalizer.normalize(text)
        self.redis.zrem(self.vocabulary_key, normalized_text)
        for token in self.tokenizer.tokenize(normalized_text):
            for i in range(len(token), 0, -1):
                prefix = token[:i]
                prefix_key = self._get_prefix_key(prefix)
                self.redis.zrem(prefix_key, normalized_text)
                self._rebuild_prefix_set(prefix)
        self.metadata_storage.delete(normalized_text)
