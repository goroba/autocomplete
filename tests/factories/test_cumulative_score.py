from unittest.mock import Mock

from autocomplete.click_buffers import RedisClickBuffer
from autocomplete.engines import CumulativeScoreEngine
from autocomplete.factories import create_cumulative_score_engine
from autocomplete.metadata import RedisMetadataStorage
from autocomplete.normalizers import LowercaseNormalizer
from autocomplete.tokenizers import WhitespaceTokenizer


def test_create_cumulative_score_engine_wires_components():
    redis = Mock()
    client = create_cumulative_score_engine("ac", redis)

    assert isinstance(client, CumulativeScoreEngine)
    assert client.name == "ac"
    assert client.redis is redis
    assert isinstance(client.normalizer, LowercaseNormalizer)
    assert isinstance(client.tokenizer, WhitespaceTokenizer)
    assert isinstance(client.metadata_storage, RedisMetadataStorage)
    assert isinstance(client.click_buffer, RedisClickBuffer)
    assert client.top_n == 5


def test_create_cumulative_score_engine_accepts_custom_top_n():
    redis = Mock()
    client = create_cumulative_score_engine("ac", redis, top_n=10)

    assert client.top_n == 10


def test_create_cumulative_score_engine_store_uses_prefix_keys():
    redis = Mock()
    client = create_cumulative_score_engine("ac", redis)

    client.store("Red Apple")

    redis.zadd.assert_any_call("ac:prefix:red", {"Red Apple": 0})
    redis.zadd.assert_any_call("ac:prefix:apple", {"Red Apple": 0})


def test_create_cumulative_score_engine_store_persists_metadata():
    redis = Mock()
    client = create_cumulative_score_engine("ac", redis)

    client.store("Hello", metadata={"category": "greeting"})

    redis.hset.assert_called_once_with(
        "ac:metadata:hello",
        mapping={"category": "greeting"},
    )


def test_create_cumulative_score_engine_search_returns_results_with_metadata():
    redis = Mock()
    redis.zrevrange.return_value = [("red apple", 1.0)]
    redis.hgetall.return_value = {"category": "fruit"}
    client = create_cumulative_score_engine("ac", redis)

    results = client.search("app")

    redis.zrevrange.assert_called_once_with(
        "ac:prefix:app",
        0,
        4,
        withscores=True,
    )
    assert results == [("red apple", 1.0, {"category": "fruit"})]
