from unittest.mock import Mock

from autocomplete.clients.redis.simple_trie_client import SimpleTrieClient
from autocomplete.metadata.redis.redis_metadata_storage import RedisMetadataStorage
from autocomplete.normalizers.lowercase_normalizer import LowercaseNormalizer
from autocomplete.prototypes.simple_trie import SimpleTrie
from autocomplete.tokenizers.no_split_tokenizer import NoSplitTokenizer


def test_simple_trie_wires_components():
    redis = Mock()
    prototype = SimpleTrie("ac", redis)

    assert isinstance(prototype.client, SimpleTrieClient)
    assert prototype.client.prefix == "ac"
    assert prototype.client.redis is redis
    assert isinstance(prototype.client.normalizer, LowercaseNormalizer)
    assert isinstance(prototype.client.tokenizer, NoSplitTokenizer)
    assert isinstance(prototype.client.metadata_storage, RedisMetadataStorage)
    assert prototype.client.top_n == 5
    assert prototype.client.scoreable is True


def test_simple_trie_accepts_custom_options():
    redis = Mock()
    prototype = SimpleTrie("ac", redis, top_n=10, scoreable=False)

    assert prototype.client.top_n == 10
    assert prototype.client.scoreable is False


def test_simple_trie_store_uses_prefix_trie():
    redis = Mock()
    prototype = SimpleTrie("ac", redis)

    prototype.store("Hello", score=1.5)

    redis.zadd.assert_called_once_with("ac:prefix:hello", {"Hello": 1.5})


def test_simple_trie_store_persists_metadata():
    redis = Mock()
    prototype = SimpleTrie("ac", redis)

    prototype.store("Hello", metadata={"category": "greeting"})

    redis.hset.assert_called_once_with(
        "ac:metadata:Hello",
        mapping={"category": "greeting"},
    )


def test_simple_trie_search_returns_results_with_metadata():
    redis = Mock()
    redis.zrevrange.return_value = [("Hello", 1.5)]
    redis.hgetall.return_value = {"category": "greeting"}
    prototype = SimpleTrie("ac", redis)

    results = prototype.search("hel")

    redis.zrevrange.assert_called_once_with("ac:prefix:hel", 0, 4, withscores=True)
    assert results == [("Hello", 1.5, {"category": "greeting"})]
