import json
from unittest.mock import Mock

from autocomplete.click_buffers import NoopClickBuffer, RedisClickBuffer
from autocomplete.factories import create_redis_search_scored_index
from autocomplete.indexes import RediSearchScoredIndex
from autocomplete.normalizers import LowercaseNormalizer, NoopNormalizer


def _index(**kwargs) -> RediSearchScoredIndex:
    redis = kwargs.pop("redis", Mock())
    name = kwargs.pop("name", "ac")
    return RediSearchScoredIndex(
        name,
        redis,
        normalizer=LowercaseNormalizer(),
        **kwargs,
    )


def test_redis_search_scored_index_stores_dependencies():
    normalizer = LowercaseNormalizer()
    redis = Mock()

    client = RediSearchScoredIndex("ac", redis, normalizer=normalizer)

    assert client.name == "ac"
    assert client.redis is redis
    assert client.normalizer is normalizer
    assert client.top_n == 5
    assert client.suggestions_key == "ac:suggestions"
    assert client.fuzzy is False
    assert isinstance(client.click_buffer, NoopClickBuffer)


def test_store_adds_suggestion():
    redis = Mock()
    client = _index(redis=redis)

    client.store("Apple", score=1.0)

    redis.execute_command.assert_called_once_with(
        "FT.SUGADD",
        "ac:suggestions",
        "apple",
        1.0,
    )


def test_store_attaches_metadata_payload():
    redis = Mock()
    client = _index(redis=redis)

    client.store("Apple", metadata={"category": "fruit"})

    redis.execute_command.assert_called_once_with(
        "FT.SUGADD",
        "ac:suggestions",
        "apple",
        0,
        "PAYLOAD",
        json.dumps({"category": "fruit"}),
    )


def test_rescore_uses_incr():
    redis = Mock()
    client = _index(redis=redis)

    client.rescore("Apple", 1.0)

    redis.execute_command.assert_called_once_with(
        "FT.SUGADD",
        "ac:suggestions",
        "apple",
        1.0,
        "INCR",
    )


def test_flush_processes_click_buffer_with_incr():
    redis = Mock()
    click_buffer = Mock(spec=RedisClickBuffer)

    def batched_flush():
        yield ("Red Apple", 1.0)
        yield ("Banana", 2.0)

    click_buffer.flush.return_value = batched_flush()
    client = _index(redis=redis, click_buffer=click_buffer)

    client.flush()

    click_buffer.flush.assert_called_once()
    assert redis.execute_command.call_count == 2
    redis.execute_command.assert_any_call(
        "FT.SUGADD",
        "ac:suggestions",
        "red apple",
        1.0,
        "INCR",
    )
    redis.execute_command.assert_any_call(
        "FT.SUGADD",
        "ac:suggestions",
        "banana",
        2.0,
        "INCR",
    )


def test_flush_with_empty_click_buffer():
    redis = Mock()
    click_buffer = Mock(spec=RedisClickBuffer)
    click_buffer.flush.return_value = iter([])
    client = _index(redis=redis, click_buffer=click_buffer)

    client.flush()

    click_buffer.flush.assert_called_once()
    redis.execute_command.assert_not_called()


def test_delete_removes_suggestion():
    redis = Mock()
    client = _index(redis=redis)

    client.delete("Red Apple")

    redis.execute_command.assert_called_once_with(
        "FT.SUGDEL",
        "ac:suggestions",
        "red apple",
    )


def test_search_returns_results_with_payload():
    redis = Mock()
    redis.execute_command.return_value = [
        "apple",
        1.0,
        json.dumps({"category": "fruit"}),
    ]
    client = _index(redis=redis)

    results = client.search("app")

    redis.execute_command.assert_called_once_with(
        "FT.SUGGET",
        "ac:suggestions",
        "app",
        "MAX",
        5,
        "WITHSCORES",
        "WITHPAYLOADS",
    )
    assert results == [("apple", 1.0, {"category": "fruit"})]


def test_search_with_fuzzy_passes_fuzzy_flag():
    redis = Mock()
    redis.execute_command.return_value = []
    client = _index(redis=redis, fuzzy=True)

    client.search("app")

    redis.execute_command.assert_called_once_with(
        "FT.SUGGET",
        "ac:suggestions",
        "app",
        "MAX",
        5,
        "FUZZY",
        "WITHSCORES",
        "WITHPAYLOADS",
    )


def test_search_returns_empty_for_empty_query():
    redis = Mock()
    client = _index(redis=redis)

    results = client.search("   ")

    assert results == []
    redis.execute_command.assert_not_called()


def test_create_redis_search_scored_index_wires_components():
    redis = Mock()
    client = create_redis_search_scored_index("ac", redis)

    assert isinstance(client, RediSearchScoredIndex)
    assert client.name == "ac"
    assert client.redis is redis
    assert isinstance(client.normalizer, NoopNormalizer)
    assert isinstance(client.click_buffer, RedisClickBuffer)
    assert client.top_n == 5
