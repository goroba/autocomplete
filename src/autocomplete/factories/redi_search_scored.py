from __future__ import annotations

from typing import TYPE_CHECKING

from autocomplete.click_buffers import ClickBuffer, RedisClickBuffer
from autocomplete.indexes import RediSearchScoredIndex
from autocomplete.normalizers import Normalizer

if TYPE_CHECKING:
    from redis import Redis


def create_redis_search_scored_index(
    name: str,
    redis: Redis,
    *,
    top_n: int = 5,
    fuzzy: bool = False,
    normalizer: Normalizer | None = None,
    click_buffer: ClickBuffer | None = None,
) -> RediSearchScoredIndex:
    return RediSearchScoredIndex(
        name,
        redis,
        top_n=top_n,
        fuzzy=fuzzy,
        normalizer=normalizer,
        click_buffer=click_buffer or RedisClickBuffer(name, redis),
    )
