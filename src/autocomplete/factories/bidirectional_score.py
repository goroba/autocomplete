from __future__ import annotations

from typing import TYPE_CHECKING

from autocomplete.click_buffers import ClickBuffer, RedisClickBuffer
from autocomplete.engines import BidirectionalScoreEngine
from autocomplete.metadata import MetadataStorage, RedisMetadataStorage
from autocomplete.normalizers import LowercaseNormalizer, Normalizer
from autocomplete.tokenizers import Tokenizer, WhitespaceTokenizer

if TYPE_CHECKING:
    from redis import Redis


def create_bidirectional_score_engine(
    name: str,
    redis: Redis,
    *,
    top_n: int = 5,
    normalizer: Normalizer | None = None,
    tokenizer: Tokenizer | None = None,
    metadata_storage: MetadataStorage | None = None,
    click_buffer: ClickBuffer | None = None,
) -> BidirectionalScoreEngine:
    return BidirectionalScoreEngine(
        name,
        redis,
        top_n=top_n,
        normalizer=normalizer or LowercaseNormalizer(),
        tokenizer=tokenizer or WhitespaceTokenizer(),
        metadata_storage=metadata_storage or RedisMetadataStorage(name, redis),
        click_buffer=click_buffer or RedisClickBuffer(name, redis),
    )
