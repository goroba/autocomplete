from __future__ import annotations

from typing import TYPE_CHECKING

from autocomplete.engines import ScorelessEngine
from autocomplete.metadata import MetadataStorage, RedisMetadataStorage
from autocomplete.normalizers import NoopNormalizer, Normalizer

if TYPE_CHECKING:
    from redis import Redis


def create_scoreless_engine(
    name: str,
    redis: Redis,
    *,
    top_n: int = 5,
    normalizer: Normalizer | None = None,
    metadata_storage: MetadataStorage | None = None,
) -> ScorelessEngine:
    return ScorelessEngine(
        name,
        redis,
        normalizer=normalizer or NoopNormalizer(),
        top_n=top_n,
        metadata_storage=metadata_storage or RedisMetadataStorage(name, redis),
    )
