from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from autocomplete.click_buffers import ClickBuffer
from autocomplete.engines import Engine

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
        self.engine: Engine | None = None
        self.buffer_key: str = f"{self.name}:click_buffer"

    def set_engine(self, engine: Engine) -> None:
        self.engine = engine

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
