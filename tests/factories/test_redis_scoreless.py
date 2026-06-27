from unittest.mock import Mock

from autocomplete.indexes import RedisScorelessIndex
from autocomplete.factories import create_redis_scoreless_index
from autocomplete.metadata import RedisMetadataStorage
from autocomplete.normalizers import NoopNormalizer


def test_create_redis_scoreless_index_wires_components():
    redis = Mock()
    client = create_redis_scoreless_index("ac", redis)

    assert isinstance(client, RedisScorelessIndex)
    assert client.name == "ac"
    assert client.redis is redis
    assert isinstance(client.normalizer, NoopNormalizer)
    assert isinstance(client.metadata_storage, RedisMetadataStorage)
    assert client.top_n == 5


def test_create_redis_scoreless_index_accepts_custom_top_n():
    redis = Mock()
    client = create_redis_scoreless_index("ac", redis, top_n=10)

    assert client.top_n == 10


def test_create_redis_scoreless_index_store_uses_trie_key():
    redis = Mock()
    client = create_redis_scoreless_index("ac", redis)

    client.store("Hello")

    redis.zadd.assert_called_once_with("ac:trie", {"Hello": 0})


def test_create_redis_scoreless_index_store_persists_metadata():
    redis = Mock()
    client = create_redis_scoreless_index("ac", redis)

    client.store("Hello", metadata={"category": "greeting"})

    redis.hset.assert_called_once_with(
        "ac:metadata:Hello",
        mapping={"category": "greeting"},
    )


def test_create_redis_scoreless_index_search_returns_results_with_metadata():
    redis = Mock()
    redis.zrange.return_value = ["hello"]
    redis.hgetall.return_value = {"category": "greeting"}
    client = create_redis_scoreless_index("ac", redis)

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
