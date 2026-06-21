from unittest.mock import Mock

import pytest

from autocomplete.clients.redis.simple_trie_client import SimpleTrieClient
from autocomplete.metadata.redis.redis_metadata_storage import RedisMetadataStorage
from autocomplete.normalizers.lowercase_normalizer import LowercaseNormalizer
from autocomplete.tokenizers.whitespace_tokenizer import WhitespaceTokenizer


def _client(**kwargs) -> SimpleTrieClient:
    redis = kwargs.pop("redis", Mock())
    prefix = kwargs.pop("prefix", "ac")
    return SimpleTrieClient(
        prefix,
        redis,
        normalizer=LowercaseNormalizer(),
        tokenizer=WhitespaceTokenizer(),
        **kwargs,
    )


def test_simple_trie_client_stores_dependencies():
    normalizer = LowercaseNormalizer()
    tokenizer = WhitespaceTokenizer()
    redis = Mock()

    client = SimpleTrieClient("ac", redis, normalizer=normalizer, tokenizer=tokenizer)

    assert client.prefix == "ac"
    assert client.redis is redis
    assert client.normalizer is normalizer
    assert client.tokenizer is tokenizer
    assert client.top_n == 5
    assert client.scoreable is True
    assert client.metadata_storage is None


def test_simple_trie_client_accepts_custom_scoreable():
    client = _client(scoreable=False)

    assert client.scoreable is False


def test_store_adds_normalized_tokens_to_sorted_sets():
    redis = Mock()
    client = SimpleTrieClient(
        "ac",
        redis,
        normalizer=LowercaseNormalizer(),
        tokenizer=WhitespaceTokenizer(),
    )

    client.store("Hello World", score=1.5)

    redis.zadd.assert_any_call("ac:prefix:hello", {"Hello World": 1.5})
    redis.zadd.assert_any_call("ac:prefix:world", {"Hello World": 1.5})
    assert redis.zadd.call_count == 2
    redis.hset.assert_not_called()


def test_store_uses_default_score():
    redis = Mock()
    client = SimpleTrieClient(
        "ac",
        redis,
        normalizer=LowercaseNormalizer(),
        tokenizer=WhitespaceTokenizer(),
    )

    client.store("Hello")

    redis.zadd.assert_called_once_with("ac:prefix:hello", {"Hello": 0.0})


def test_store_persists_metadata_when_storage_defined():
    redis = Mock()
    client = SimpleTrieClient(
        "ac",
        redis,
        normalizer=LowercaseNormalizer(),
        tokenizer=WhitespaceTokenizer(),
        metadata_storage=RedisMetadataStorage("ac", redis),
    )

    client.store("Hello", metadata={"category": "greeting"})

    redis.hset.assert_called_once_with(
        "ac:metadata:Hello",
        mapping={"category": "greeting"},
    )


def test_store_rejects_metadata_without_storage():
    client = _client()

    with pytest.raises(ValueError, match="metadata_storage"):
        client.store("Hello", metadata={"category": "greeting"})
