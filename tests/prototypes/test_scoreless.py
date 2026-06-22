from unittest.mock import Mock

from autocomplete.clients.redis.scoreless_client import ScorelessClient
from autocomplete.metadata.redis.redis_metadata_storage import RedisMetadataStorage
from autocomplete.normalizers.noop_normalizer import NoopNormalizer
from autocomplete.prototypes.scoreless import Scoreless
from autocomplete.tokenizers.noop_tokenizer import NoopTokenizer


def test_scoreless_wires_components():
    redis = Mock()
    prototype = Scoreless("ac", redis)

    assert isinstance(prototype.client, ScorelessClient)
    assert prototype.client.name == "ac"
    assert prototype.client.redis is redis
    assert isinstance(prototype.client.normalizer, NoopNormalizer)
    assert isinstance(prototype.client.tokenizer, NoopTokenizer)
    assert isinstance(prototype.client.metadata_storage, RedisMetadataStorage)
    assert prototype.client.top_n == 5


def test_scoreless_accepts_custom_top_n():
    redis = Mock()
    prototype = Scoreless("ac", redis, top_n=10)

    assert prototype.client.top_n == 10


def test_scoreless_store_uses_trie_key():
    redis = Mock()
    prototype = Scoreless("ac", redis)

    prototype.store("Hello")

    redis.zadd.assert_called_once_with("ac:trie", {"Hello": 0})


def test_scoreless_store_persists_metadata():
    redis = Mock()
    prototype = Scoreless("ac", redis)

    prototype.store("Hello", metadata={"category": "greeting"})

    redis.hset.assert_called_once_with(
        "ac:metadata:Hello",
        mapping={"category": "greeting"},
    )


def test_scoreless_search_returns_results_with_metadata():
    redis = Mock()
    redis.zrange.return_value = [("hello", 0.0)]
    redis.hgetall.return_value = {"category": "greeting"}
    prototype = Scoreless("ac", redis)

    results = prototype.search("hel")

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
