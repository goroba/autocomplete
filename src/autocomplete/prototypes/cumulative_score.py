from __future__ import annotations

from typing import TYPE_CHECKING

from autocomplete.clients.redis.cumulative_score_client import CumulativeScoreClient
from autocomplete.metadata.redis.redis_metadata_storage import RedisMetadataStorage
from autocomplete.normalizers.lowercase_normalizer import LowercaseNormalizer
from autocomplete.prototypes.module_prototype import ModulePrototype
from autocomplete.tokenizers.whitespace_tokenizer import WhitespaceTokenizer

if TYPE_CHECKING:
    from redis import Redis


class CumulativeScore(ModulePrototype):
    def __init__(
        self,
        name: str,
        redis: Redis,
        *,
        top_n: int = 5,
    ) -> None:
        self._client = CumulativeScoreClient(
            name,
            redis,
            normalizer=LowercaseNormalizer(),
            tokenizer=WhitespaceTokenizer(),
            top_n=top_n,
            metadata_storage=RedisMetadataStorage(name, redis),
        )

    @property
    def client(self) -> CumulativeScoreClient:
        return self._client
