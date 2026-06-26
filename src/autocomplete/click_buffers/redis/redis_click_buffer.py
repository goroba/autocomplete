from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from autocomplete.click_buffers import ClickBuffer

if TYPE_CHECKING:
    from redis import Redis


class RedisClickBuffer(ClickBuffer):
    def __init__(
        self,
        name: str,
        redis: Redis,
        *,
        click_rate: float = 1.0,
        flush_batch_size: int = 10,
    ) -> None:
        self.name = name
        self.redis = redis
        self.click_rate = click_rate
        self.flush_batch_size = flush_batch_size
        self.buffer_key: str = f"{self.name}:click_buffer"

    def click_to_score(self, clicks: int) -> float:
        return clicks * self.click_rate

    def click(self, text: str, *, clicks: int = 1) -> None:
        self.redis.zincrby(self.buffer_key, self.click_to_score(clicks), text)

    def flush(self) -> Iterator[tuple[str, float]]:
        while True:
            batch = self.redis.zpopmax(self.buffer_key, count=self.flush_batch_size)
            if not batch:
                return
            yield from batch

    def __iter__(self) -> Iterator[tuple[str, float]]:
        offset = 0
        while True:
            batch = self.redis.zrange(
                self.buffer_key,
                offset,
                offset + self.flush_batch_size - 1,
                withscores=True,
            )
            if not batch:
                return
            yield from batch
            if len(batch) < self.flush_batch_size:
                return
            offset += self.flush_batch_size
