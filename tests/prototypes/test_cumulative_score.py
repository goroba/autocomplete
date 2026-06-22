from unittest.mock import Mock

from autocomplete.clients.redis.cumulative_score_client import CumulativeScoreClient
from autocomplete.metadata.redis.redis_metadata_storage import RedisMetadataStorage
from autocomplete.normalizers.lowercase_normalizer import LowercaseNormalizer
from autocomplete.prototypes.cumulative_score import CumulativeScore
from autocomplete.tokenizers.whitespace_tokenizer import WhitespaceTokenizer


def test_cumulative_score_wires_components():
    redis = Mock()
    prototype = CumulativeScore("ac", redis)

    assert isinstance(prototype.client, CumulativeScoreClient)
    assert prototype.client.name == "ac"
    assert prototype.client.redis is redis
    assert isinstance(prototype.client.normalizer, LowercaseNormalizer)
    assert isinstance(prototype.client.tokenizer, WhitespaceTokenizer)
    assert isinstance(prototype.client.metadata_storage, RedisMetadataStorage)
    assert prototype.client.top_n == 5


def test_cumulative_score_accepts_custom_top_n():
    redis = Mock()
    prototype = CumulativeScore("ac", redis, top_n=10)

    assert prototype.client.top_n == 10


def test_cumulative_score_store_uses_prefix_keys():
    redis = Mock()
    prototype = CumulativeScore("ac", redis)

    prototype.store("Red Apple")

    redis.zadd.assert_any_call("ac:prefix:red", {"Red Apple": 0})
    redis.zadd.assert_any_call("ac:prefix:apple", {"Red Apple": 0})


def test_cumulative_score_store_persists_metadata():
    redis = Mock()
    prototype = CumulativeScore("ac", redis)

    prototype.store("Hello", metadata={"category": "greeting"})

    redis.hset.assert_called_once_with(
        "ac:metadata:hello",
        mapping={"category": "greeting"},
    )


def test_cumulative_score_search_returns_results_with_metadata():
    redis = Mock()
    redis.zrevrange.return_value = [("red apple", 1.0)]
    redis.hgetall.return_value = {"category": "fruit"}
    prototype = CumulativeScore("ac", redis)

    results = prototype.search("app")

    redis.zrevrange.assert_called_once_with(
        "ac:prefix:app",
        0,
        4,
        withscores=True,
    )
    assert results == [("red apple", 1.0, {"category": "fruit"})]
