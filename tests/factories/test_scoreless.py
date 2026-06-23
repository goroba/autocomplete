from unittest.mock import Mock

from autocomplete.engines import ScorelessEngine
from autocomplete.factories import create_scoreless_engine
from autocomplete.metadata import RedisMetadataStorage
from autocomplete.normalizers import NoopNormalizer
from autocomplete.tokenizers import NoopTokenizer


def test_create_scoreless_engine_wires_components():
    redis = Mock()
    client = create_scoreless_engine("ac", redis)

    assert isinstance(client, ScorelessEngine)
    assert client.name == "ac"
    assert client.redis is redis
    assert isinstance(client.normalizer, NoopNormalizer)
    assert isinstance(client.tokenizer, NoopTokenizer)
    assert isinstance(client.metadata_storage, RedisMetadataStorage)
    assert client.top_n == 5


def test_create_scoreless_engine_accepts_custom_top_n():
    redis = Mock()
    client = create_scoreless_engine("ac", redis, top_n=10)

    assert client.top_n == 10


def test_create_scoreless_engine_store_uses_trie_key():
    redis = Mock()
    client = create_scoreless_engine("ac", redis)

    client.store("Hello")

    redis.zadd.assert_called_once_with("ac:trie", {"Hello": 0})


def test_create_scoreless_engine_store_persists_metadata():
    redis = Mock()
    client = create_scoreless_engine("ac", redis)

    client.store("Hello", metadata={"category": "greeting"})

    redis.hset.assert_called_once_with(
        "ac:metadata:Hello",
        mapping={"category": "greeting"},
    )


def test_create_scoreless_engine_search_returns_results_with_metadata():
    redis = Mock()
    redis.zrange.return_value = [("hello", 0.0)]
    redis.hgetall.return_value = {"category": "greeting"}
    client = create_scoreless_engine("ac", redis)

    results = client.search("hel")

    redis.zrange.assert_called_once_with(
        "ac:trie",
        "[hel",
        "[hel\xff",
        bylex=True,
        offset=0,
        num=5,
        withscores=True,
    )
    assert results == [("hello", 0.0, {"category": "greeting"})]
