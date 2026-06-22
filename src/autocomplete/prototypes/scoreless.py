from __future__ import annotations

from typing import TYPE_CHECKING

from autocomplete.clients.redis.scoreless_client import ScorelessClient
from autocomplete.metadata.redis.redis_metadata_storage import RedisMetadataStorage
from autocomplete.normalizers.noop_normalizer import NoopNormalizer
from autocomplete.prototypes.module_prototype import ModulePrototype

if TYPE_CHECKING:
    from redis import Redis


class Scoreless(ModulePrototype):
    def __init__(
        self,
        name: str,
        redis: Redis,
        *,
        top_n: int = 5,
    ) -> None:
        self._client = ScorelessClient(
            name,
            redis,
            normalizer=NoopNormalizer(),
            top_n=top_n,
            metadata_storage=RedisMetadataStorage(name, redis),
        )

    @property
    def client(self) -> ScorelessClient:
        return self._client
