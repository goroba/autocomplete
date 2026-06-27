from __future__ import annotations

from typing import TYPE_CHECKING

from autocomplete.indexes import RedisScorelessIndex
from autocomplete.metadata import MetadataStorage, RedisMetadataStorage
from autocomplete.normalizers import Normalizer

if TYPE_CHECKING:
    from redis import Redis


def create_redis_scoreless_index(
    name: str,
    redis: Redis,
    *,
    top_n: int = 5,
    normalizer: Normalizer | None = None,
    metadata_storage: MetadataStorage | None = None,
) -> RedisScorelessIndex:
    return RedisScorelessIndex(
        name,
        redis,
        normalizer=normalizer,
        top_n=top_n,
        metadata_storage=metadata_storage or RedisMetadataStorage(name, redis),
    )
