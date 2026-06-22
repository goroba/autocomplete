from unittest.mock import Mock

from autocomplete.clients.redis.scoreless_trie_client import ScorelessTrieClient
from autocomplete.metadata import NullMetadataStorage
from autocomplete.metadata.redis.redis_metadata_storage import RedisMetadataStorage
from autocomplete.normalizers.lowercase_normalizer import LowercaseNormalizer
from autocomplete.tokenizers.noop_tokenizer import NoopTokenizer


def _client(**kwargs) -> ScorelessTrieClient:
    redis = kwargs.pop("redis", Mock())
    prefix = kwargs.pop("prefix", "ac")
    return ScorelessTrieClient(
        prefix,
        redis,
        normalizer=LowercaseNormalizer(),
        **kwargs,
    )


def test_scoreless_trie_client_stores_dependencies():
    normalizer = LowercaseNormalizer()
    redis = Mock()

    client = ScorelessTrieClient("ac", redis, normalizer=normalizer)

    assert client.name == "ac"
    assert client.redis is redis
    assert client.normalizer is normalizer
    assert isinstance(client.tokenizer, NoopTokenizer)
    assert client.top_n == 5
    assert isinstance(client.metadata_storage, NullMetadataStorage)


def test_store_adds_normalized_text_to_trie_sorted_set():
    redis = Mock()
    client = _client(redis=redis)

    client.store("Hello World")

    redis.zadd.assert_called_once_with("ac:trie", {"hello world": 0})
    redis.hset.assert_not_called()


def test_store_persists_metadata_when_storage_defined():
    redis = Mock()
    client = ScorelessTrieClient(
        "ac",
        redis,
        normalizer=LowercaseNormalizer(),
        metadata_storage=RedisMetadataStorage("ac", redis),
    )

    client.store("Hello", metadata={"category": "greeting"})

    redis.hset.assert_called_once_with(
        "ac:metadata:hello",
        mapping={"category": "greeting"},
    )


def test_store_ignores_metadata_with_null_storage():
    client = _client()

    client.store("Hello", metadata={"category": "greeting"})

    client.redis.zadd.assert_called_once_with("ac:trie", {"hello": 0})
    client.redis.hset.assert_not_called()


def test_search_returns_results_with_metadata():
    redis = Mock()
    redis.zrange.return_value = [("hello", 0.0)]
    client = ScorelessTrieClient(
        "ac",
        redis,
        normalizer=LowercaseNormalizer(),
        metadata_storage=RedisMetadataStorage("ac", redis),
    )
    redis.hgetall.return_value = {"category": "greeting"}

    results = client.search("hel")

    redis.zrange.assert_called_once_with(
        "ac:trie:",
        "[hel",
        "[hel\xff",
        bylex=True,
        offset=0,
        num=5,
        withscores=True,
    )
    assert results == [("hello", 0.0, {"category": "greeting"})]


def test_search_returns_empty_for_short_query():
    redis = Mock()
    client = _client(redis=redis, min_query_length=3)

    results = client.search("he")

    assert results == []
    redis.zrange.assert_not_called()


def test_click_increments_score_on_trie_key():
    redis = Mock()
    client = _client(redis=redis)

    client.click("Hello")

    redis.zincrby.assert_called_once_with("ac:trie", 1, "hello")


def test_delete_removes_from_trie_and_metadata():
    redis = Mock()
    client = ScorelessTrieClient(
        "ac",
        redis,
        normalizer=LowercaseNormalizer(),
        metadata_storage=RedisMetadataStorage("ac", redis),
    )

    client.delete("Hello")

    redis.zrem.assert_called_once_with("ac:trie", "hello")
    redis.hdel.assert_called_once_with("ac:metadata:hello")
