from unittest.mock import Mock

from autocomplete.click_buffers.redis.redis_click_buffer import RedisClickBuffer
from autocomplete.clients.redis.cumulative_score_client import CumulativeScoreClient
from autocomplete.metadata import NullMetadataStorage
from autocomplete.metadata.redis.redis_metadata_storage import RedisMetadataStorage
from autocomplete.normalizers.lowercase_normalizer import LowercaseNormalizer
from autocomplete.tokenizers.whitespace_tokenizer import WhitespaceTokenizer


def _client(**kwargs) -> CumulativeScoreClient:
    redis = kwargs.pop("redis", Mock())
    prefix = kwargs.pop("prefix", "ac")
    return CumulativeScoreClient(
        prefix,
        redis,
        normalizer=LowercaseNormalizer(),
        tokenizer=WhitespaceTokenizer(),
        **kwargs,
    )


def test_cumulative_score_client_stores_dependencies():
    normalizer = LowercaseNormalizer()
    tokenizer = WhitespaceTokenizer()
    redis = Mock()

    client = CumulativeScoreClient("ac", redis, normalizer=normalizer, tokenizer=tokenizer)

    assert client.name == "ac"
    assert client.redis is redis
    assert client.normalizer is normalizer
    assert client.tokenizer is tokenizer
    assert client.top_n == 5
    assert isinstance(client.metadata_storage, NullMetadataStorage)


def test_store_adds_all_token_prefixes_to_sorted_sets():
    redis = Mock()
    client = _client(redis=redis)

    client.store("Apple")

    expected_keys = [
        "ac:prefix:a",
        "ac:prefix:ap",
        "ac:prefix:app",
        "ac:prefix:appl",
        "ac:prefix:apple",
    ]
    assert redis.zadd.call_count == 5
    for key in expected_keys:
        redis.zadd.assert_any_call(key, {"Apple": 0})
    assert redis.zremrangebyrank.call_count == 5
    for key in expected_keys:
        redis.zremrangebyrank.assert_any_call(key, 0, -6)


def test_store_adds_multi_token_text_to_all_token_prefix_chains():
    redis = Mock()
    client = _client(redis=redis)

    client.store("Red Apple")

    expected_keys = [
        "ac:prefix:r",
        "ac:prefix:re",
        "ac:prefix:red",
        "ac:prefix:a",
        "ac:prefix:ap",
        "ac:prefix:app",
        "ac:prefix:appl",
        "ac:prefix:apple",
    ]
    assert redis.zadd.call_count == 8
    for key in expected_keys:
        redis.zadd.assert_any_call(key, {"Red Apple": 0})


def test_store_uses_provided_score():
    redis = Mock()
    client = _client(redis=redis)

    client.store("Apple", score=10)

    redis.zadd.assert_any_call("ac:prefix:a", {"Apple": 10})


def test_store_persists_metadata_when_storage_defined():
    redis = Mock()
    client = CumulativeScoreClient(
        "ac",
        redis,
        normalizer=LowercaseNormalizer(),
        tokenizer=WhitespaceTokenizer(),
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

    client.redis.hset.assert_not_called()


def test_search_single_token_returns_original_text():
    redis = Mock()
    redis.zrevrange.return_value = [("Apple", 1.0)]
    client = CumulativeScoreClient(
        "ac",
        redis,
        normalizer=LowercaseNormalizer(),
        tokenizer=WhitespaceTokenizer(),
        metadata_storage=RedisMetadataStorage("ac", redis),
    )
    redis.hgetall.return_value = {"category": "fruit"}

    results = client.search("app")

    redis.zrevrange.assert_called_once_with(
        "ac:prefix:app",
        0,
        4,
        withscores=True,
    )
    assert results == [("Apple", 1.0, {"category": "fruit"})]
    redis.hgetall.assert_called_once_with("ac:metadata:apple")


def test_search_multi_token_uses_zinterstore():
    redis = Mock()
    redis.zrevrange.return_value = [("Red Apple", 2.0)]
    client = CumulativeScoreClient(
        "ac",
        redis,
        normalizer=LowercaseNormalizer(),
        tokenizer=WhitespaceTokenizer(),
        metadata_storage=RedisMetadataStorage("ac", redis),
    )
    redis.hgetall.return_value = {}

    results = client.search("red app")

    redis.zinterstore.assert_called_once()
    interstore_call = redis.zinterstore.call_args
    temp_key = interstore_call.args[0]
    assert temp_key.startswith("ac:search:")
    assert interstore_call.args[1] == ["ac:prefix:red", "ac:prefix:app"]
    assert interstore_call.kwargs == {"aggregate": "MAX"}
    redis.zrevrange.assert_called_once_with(
        temp_key,
        0,
        4,
        withscores=True,
    )
    redis.delete.assert_called_once_with(temp_key)
    assert results == [("Red Apple", 2.0, {})]


def test_search_multi_token_with_short_token():
    redis = Mock()
    redis.zinterstore.return_value = 1
    redis.zrevrange.return_value = [("Red Apple", 1.0)]
    client = _client(redis=redis)

    results = client.search("re app")

    redis.zinterstore.assert_called_once()
    assert results == [("Red Apple", 1.0, {})]


def test_search_returns_empty_for_empty_query():
    redis = Mock()
    client = _client(redis=redis)

    results = client.search("   ")

    assert results == []
    redis.zrevrange.assert_not_called()


def test_click_increments_score_on_all_prefix_keys():
    redis = Mock()
    client = _client(redis=redis)

    client.click("Red Apple")

    redis.zincrby.assert_not_called()
    redis.zremrangebyrank.assert_not_called()


def test_rescore_increments_all_prefix_keys():
    redis = Mock()
    pipe = Mock()
    redis.pipeline.return_value = pipe
    client = _client(redis=redis)

    client.rescore("Red Apple", 2.5)

    expected_keys = [
        "ac:prefix:r",
        "ac:prefix:re",
        "ac:prefix:red",
        "ac:prefix:a",
        "ac:prefix:ap",
        "ac:prefix:app",
        "ac:prefix:appl",
        "ac:prefix:apple",
    ]
    redis.pipeline.assert_called_once()
    assert pipe.zincrby.call_count == 8
    for key in expected_keys:
        pipe.zincrby.assert_any_call(key, 2.5, "Red Apple")
    pipe.execute.assert_called_once()


def test_rescore_keeps_member_in_top_n():
    redis = Mock()
    pipe = Mock()
    redis.pipeline.return_value = pipe
    client = _client(redis=redis)

    client.rescore("Apple", 1.0)

    redis.zrevrank.assert_not_called()
    redis.zrem.assert_not_called()
    assert pipe.zremrangebyrank.call_count == 5
    pipe.execute.assert_called_once()


def test_rescore_trims_member_outside_top_n():
    redis = Mock()
    pipe = Mock()
    redis.pipeline.return_value = pipe
    client = _client(redis=redis)

    client.rescore("Apple", 1.0)

    redis.zrevrank.assert_not_called()
    redis.zrem.assert_not_called()
    assert pipe.zremrangebyrank.call_count == 5
    pipe.execute.assert_called_once()


def test_delete_removes_from_all_prefix_keys_and_metadata():
    redis = Mock()
    client = CumulativeScoreClient(
        "ac",
        redis,
        normalizer=LowercaseNormalizer(),
        tokenizer=WhitespaceTokenizer(),
        metadata_storage=RedisMetadataStorage("ac", redis),
    )

    client.delete("Red Apple")

    expected_keys = [
        "ac:prefix:r",
        "ac:prefix:re",
        "ac:prefix:red",
        "ac:prefix:a",
        "ac:prefix:ap",
        "ac:prefix:app",
        "ac:prefix:appl",
        "ac:prefix:apple",
    ]
    assert redis.zrem.call_count == 8
    for key in expected_keys:
        redis.zrem.assert_any_call(key, "Red Apple")
    redis.hdel.assert_called_once_with("ac:metadata:red apple")


def test_flush_rescores_all_pairs_in_single_pipeline():
    redis = Mock()
    pipe = Mock()
    redis.pipeline.return_value = pipe
    click_buffer = Mock(spec=RedisClickBuffer)
    click_buffer.flush.return_value = iter([("Red Apple", 2.5), ("Banana", 1.0)])
    client = _client(redis=redis, click_buffer=click_buffer)

    client.flush()

    click_buffer.flush.assert_called_once()
    redis.pipeline.assert_called_once()
    assert pipe.zincrby.call_count == 14
    assert pipe.zremrangebyrank.call_count == 14
    pipe.execute.assert_called_once()


def test_flush_drains_click_buffer_and_rescores_via_pipeline():
    redis = Mock()
    pipe = Mock()
    redis.pipeline.return_value = pipe
    click_buffer = Mock(spec=RedisClickBuffer)
    click_buffer.flush.return_value = iter([("Red Apple", 1.0)])
    client = _client(redis=redis, click_buffer=click_buffer)

    client.flush()

    click_buffer.flush.assert_called_once()
    redis.pipeline.assert_called_once()
    assert pipe.zincrby.call_count == 8
    assert pipe.zremrangebyrank.call_count == 8
    pipe.execute.assert_called_once()
