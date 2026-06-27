from unittest.mock import Mock

from autocomplete.indexes import RedisScorelessIndex
from autocomplete.metadata import NullMetadataStorage, RedisMetadataStorage
from autocomplete.normalizers import LowercaseNormalizer


def _index(**kwargs) -> RedisScorelessIndex:
    redis = kwargs.pop("redis", Mock())
    prefix = kwargs.pop("prefix", "ac")
    return RedisScorelessIndex(
        prefix,
        redis,
        normalizer=LowercaseNormalizer(),
        **kwargs,
    )


def test_redis_scoreless_index_stores_dependencies():
    normalizer = LowercaseNormalizer()
    redis = Mock()

    client = RedisScorelessIndex("ac", redis, normalizer=normalizer)

    assert client.name == "ac"
    assert client.redis is redis
    assert client.normalizer is normalizer
    assert client.trie_key == "ac:trie"
    assert client.top_n == 5
    assert isinstance(client.metadata_storage, NullMetadataStorage)


def test_store_adds_normalized_text_to_trie_sorted_set():
    redis = Mock()
    client = _index(redis=redis)

    client.store("Hello World")

    redis.zadd.assert_called_once_with("ac:trie", {"hello world": 0})
    redis.hset.assert_not_called()


def test_store_persists_metadata_when_storage_defined():
    redis = Mock()
    client = RedisScorelessIndex(
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
    client = _index()

    client.store("Hello", metadata={"category": "greeting"})

    client.redis.zadd.assert_called_once_with("ac:trie", {"hello": 0})
    client.redis.hset.assert_not_called()


def test_search_returns_results_with_metadata():
    redis = Mock()
    redis.zrange.return_value = ["hello"]
    client = RedisScorelessIndex(
        "ac",
        redis,
        normalizer=LowercaseNormalizer(),
        metadata_storage=RedisMetadataStorage("ac", redis),
    )
    redis.hgetall.return_value = {"category": "greeting"}

    results = client.search("hel")

    redis.zrange.assert_called_once_with(
        "ac:trie",
        "[hel",
        "[hel\xff",
        bylex=True,
        offset=0,
        num=5,
    )
    assert results == [("hello", 0.0, {"category": "greeting"})]


def test_search_returns_empty_for_empty_query():
    redis = Mock()
    client = _index(redis=redis)

    results = client.search("")

    assert results == []
    redis.zrange.assert_not_called()


def test_click_is_noop():
    redis = Mock()
    client = _index(redis=redis)

    client.click("Hello")

    redis.zincrby.assert_not_called()


def test_delete_removes_from_trie_and_metadata():
    redis = Mock()
    client = RedisScorelessIndex(
        "ac",
        redis,
        normalizer=LowercaseNormalizer(),
        metadata_storage=RedisMetadataStorage("ac", redis),
    )

    client.delete("Hello")

    redis.zrem.assert_called_once_with("ac:trie", "hello")
    redis.hdel.assert_called_once_with("ac:metadata:hello")
