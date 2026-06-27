from unittest.mock import Mock

from autocomplete.click_buffers import RedisClickBuffer
from autocomplete.factories import create_redis_search_scored_index
from autocomplete.indexes import RediSearchScoredIndex
from autocomplete.normalizers import NoopNormalizer


def test_create_redis_search_scored_index_wires_components():
    redis = Mock()
    client = create_redis_search_scored_index("ac", redis)

    assert isinstance(client, RediSearchScoredIndex)
    assert client.name == "ac"
    assert client.redis is redis
    assert isinstance(client.normalizer, NoopNormalizer)
    assert isinstance(client.click_buffer, RedisClickBuffer)
    assert client.top_n == 5
    assert client.fuzzy is False


def test_create_redis_search_scored_index_accepts_custom_fuzzy():
    redis = Mock()
    client = create_redis_search_scored_index("ac", redis, fuzzy=True)

    assert client.fuzzy is True


def test_create_redis_search_scored_index_accepts_custom_top_n():
    redis = Mock()
    client = create_redis_search_scored_index("ac", redis, top_n=10)

    assert client.top_n == 10
