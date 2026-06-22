from __future__ import annotations

from typing import TYPE_CHECKING

from autocomplete.clients.redis.scoreless_trie_client import ScorelessTrieClient
from autocomplete.metadata.redis.redis_metadata_storage import RedisMetadataStorage
from autocomplete.normalizers.noop_normalizer import NoopNormalizer
from autocomplete.prototypes.module_prototype import ModulePrototype

if TYPE_CHECKING:
    from redis import Redis


class ScorelessTrie(ModulePrototype):
    def __init__(
        self,
        name: str,
        redis: Redis,
        *,
        top_n: int = 5,
        min_query_length: int = 1,
    ) -> None:
        self._client = ScorelessTrieClient(
            name,
            redis,
            normalizer=NoopNormalizer(),
            top_n=top_n,
            min_query_length=min_query_length,
            metadata_storage=RedisMetadataStorage(name, redis),
        )

    @property
    def client(self) -> ScorelessTrieClient:
        return self._client
