from __future__ import annotations

from typing import TYPE_CHECKING

from autocomplete.clients.redis.simple_trie_client import SimpleTrieClient
from autocomplete.metadata.redis.redis_metadata_storage import RedisMetadataStorage
from autocomplete.normalizers.lowercase_normalizer import LowercaseNormalizer
from autocomplete.prototypes.module_prototype import ModulePrototype
from autocomplete.tokenizers.no_split_tokenizer import NoSplitTokenizer

if TYPE_CHECKING:
    from redis import Redis


class SimpleTrie(ModulePrototype):
    def __init__(
        self,
        prefix: str,
        redis: Redis,
        *,
        top_n: int = 5,
        scoreable: bool = True,
    ) -> None:
        self._client = SimpleTrieClient(
            prefix,
            redis,
            normalizer=LowercaseNormalizer(),
            tokenizer=NoSplitTokenizer(),
            top_n=top_n,
            scoreable=scoreable,
            metadata_storage=RedisMetadataStorage(prefix, redis),
        )

    @property
    def client(self) -> SimpleTrieClient:
        return self._client
