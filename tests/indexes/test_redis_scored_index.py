from unittest.mock import Mock, patch

from autocomplete.click_buffers import NoopClickBuffer, RedisClickBuffer
from autocomplete.indexes import RedisScoredIndex
from autocomplete.factories import create_redis_scored_index
from autocomplete.metadata import NullMetadataStorage, RedisMetadataStorage
from autocomplete.normalizers import LowercaseNormalizer, NoopNormalizer
from autocomplete.tokenizers import NoopTokenizer, WhitespaceTokenizer


def _index(**kwargs) -> RedisScoredIndex:
    redis = kwargs.pop("redis", Mock())
    prefix = kwargs.pop("prefix", "ac")
    return RedisScoredIndex(
        prefix,
        redis,
        normalizer=LowercaseNormalizer(),
        tokenizer=WhitespaceTokenizer(),
        **kwargs,
    )


def _mock_pipeline(redis: Mock) -> Mock:
    pipe = Mock()
    redis.pipeline.return_value.__enter__ = Mock(return_value=pipe)
    redis.pipeline.return_value.__exit__ = Mock(return_value=False)
    return pipe


def test_redis_scored_index_stores_dependencies():
    normalizer = LowercaseNormalizer()
    tokenizer = WhitespaceTokenizer()
    redis = Mock()

    client = RedisScoredIndex("ac", redis, normalizer=normalizer, tokenizer=tokenizer)

    assert client.name == "ac"
    assert client.redis is redis
    assert client.normalizer is normalizer
    assert client.tokenizer is tokenizer
    assert client.top_n == 5
    assert isinstance(client.metadata_storage, NullMetadataStorage)
    assert isinstance(client.click_buffer, NoopClickBuffer)


def test_store_adds_to_vocabulary_and_prefix():
    redis = Mock()
    client = _index(redis=redis)

    client.store("Apple")

    expected_prefix_keys = [
        "ac:prefix:a",
        "ac:prefix:ap",
        "ac:prefix:app",
        "ac:prefix:appl",
        "ac:prefix:apple",
    ]
    redis.zadd.assert_any_call("ac:vocabulary", {"apple": 0})
    assert redis.zadd.call_count == 6
    for key in expected_prefix_keys:
        redis.zadd.assert_any_call(key, {"apple": 0})
    assert redis.zremrangebyrank.call_count == 5
    for key in expected_prefix_keys:
        redis.zremrangebyrank.assert_any_call(key, 0, -6)


def test_store_does_not_trim_vocabulary():
    redis = Mock()
    client = _index(redis=redis)

    client.store("Apple")

    for call in redis.zremrangebyrank.call_args_list:
        key = call.args[0]
        assert key.startswith("ac:prefix:")


def test_positive_rescore_updates_vocabulary_and_trims_full_token_prefix():
    redis = Mock()
    redis.zscore.return_value = 1.0
    client = _index(redis=redis)

    client.rescore("Apple", 1.0)

    redis.zincrby.assert_called_once_with("ac:vocabulary", 1.0, "apple")
    redis.zscore.assert_called_once_with("ac:vocabulary", "apple")
    assert redis.zadd.call_count == 5
    for prefix in ("a", "ap", "app", "appl", "apple"):
        redis.zadd.assert_any_call(f"ac:prefix:{prefix}", {"apple": 1.0})
    assert redis.zremrangebyrank.call_count == 5
    redis.pipeline.assert_not_called()


def test_negative_rescore_rebuilds_when_text_leaves_top_n():
    redis = Mock()
    redis.zscore.return_value = 2.0
    redis.zrange.return_value = ["cherry"]
    redis.zmscore.return_value = [5.0]
    pipe = _mock_pipeline(redis)
    client = _index(redis=redis)

    client.rescore("Apple", -3.0)

    redis.zincrby.assert_called_once_with("ac:vocabulary", -3.0, "apple")
    redis.zscore.assert_called_once_with("ac:vocabulary", "apple")
    assert redis.zadd.call_count == 5
    assert redis.zrange.call_count == 5
    assert redis.zmscore.call_count == 5
    assert redis.pipeline.call_count == 5
    assert pipe.delete.call_count == 5
    assert pipe.zadd.call_count == 5
    redis.zinterstore.assert_not_called()
    redis.zremrangebyrank.assert_not_called()


def test_negative_rescore_rebuilds_on_boundary_mismatch():
    redis = Mock()
    redis.zscore.return_value = 8.0
    redis.zmscore.return_value = [8.0, 10.0]

    def zrange_side_effect(key, start, end, **kwargs):
        return ["apple", "cherry"]

    redis.zrange.side_effect = zrange_side_effect
    pipe = _mock_pipeline(redis)
    client = _index(redis=redis, top_n=2)

    client.rescore("Apple", -1.0)

    assert redis.zrange.call_count == 5
    assert redis.zmscore.call_count == 5
    assert redis.pipeline.call_count == 5
    assert pipe.delete.call_count == 5
    assert pipe.zadd.call_count == 5
    for call in pipe.zadd.call_args_list:
        assert len(call.args[1]) <= 2
    redis.zinterstore.assert_not_called()
    redis.zremrangebyrank.assert_not_called()


def test_rebuild_prefix_keeps_only_top_n_by_score():
    redis = Mock()
    redis.zrange.return_value = ["apple", "apricot", "application"]
    redis.zmscore.return_value = [10.0, 20.0, 30.0]
    pipe = _mock_pipeline(redis)
    client = _index(redis=redis, top_n=2)

    client._rebuild_prefix_set("ap")

    redis.zrange.assert_called_once_with(
        "ac:vocabulary",
        "[ap",
        "[ap\xff",
        bylex=True,
    )
    redis.zmscore.assert_called_once_with(
        "ac:vocabulary",
        ["apple", "apricot", "application"],
    )
    pipe.delete.assert_called_once_with("ac:prefix:ap")
    pipe.zadd.assert_called_once_with(
        "ac:prefix:ap",
        {"application": 30.0, "apricot": 20.0},
    )
    redis.zinterstore.assert_not_called()
    redis.zremrangebyrank.assert_not_called()

def test_delete_removes_from_vocabulary_and_prefix():
    redis = Mock()
    redis.zrange.return_value = []
    client = RedisScoredIndex(
        "ac",
        redis,
        normalizer=LowercaseNormalizer(),
        tokenizer=WhitespaceTokenizer(),
        metadata_storage=RedisMetadataStorage("ac", redis),
    )

    client.delete("Red Apple")

    expected_prefix_keys = [
        "ac:prefix:r",
        "ac:prefix:re",
        "ac:prefix:red",
        "ac:prefix:a",
        "ac:prefix:ap",
        "ac:prefix:app",
        "ac:prefix:appl",
        "ac:prefix:apple",
    ]
    redis.zrem.assert_any_call("ac:vocabulary", "red apple")
    assert redis.zrem.call_count == 9
    for key in expected_prefix_keys:
        redis.zrem.assert_any_call(key, "red apple")
    redis.hdel.assert_called_once_with("ac:metadata:red apple")


def test_flush_processes_click_buffer_iterator_incrementally():
    redis = Mock()
    redis.zscore.side_effect = [1.0, 2.0]
    click_buffer = Mock(spec=RedisClickBuffer)

    def batched_flush():
        yield ("Red Apple", 1.0)
        yield ("Banana", 2.0)

    click_buffer.flush.return_value = batched_flush()
    client = _index(redis=redis, click_buffer=click_buffer)

    client.flush()

    click_buffer.flush.assert_called_once()
    assert redis.zincrby.call_count == 2
    redis.zincrby.assert_any_call("ac:vocabulary", 1.0, "red apple")
    redis.zincrby.assert_any_call("ac:vocabulary", 2.0, "banana")
    assert redis.zscore.call_count == 2
    redis.zscore.assert_any_call("ac:vocabulary", "red apple")
    redis.zscore.assert_any_call("ac:vocabulary", "banana")
    assert redis.zadd.call_count == 14
    redis.pipeline.assert_not_called()


def test_flush_drains_click_buffer_and_updates_vocabulary():
    redis = Mock()
    redis.zscore.return_value = 1.0
    click_buffer = Mock(spec=RedisClickBuffer)
    click_buffer.flush.return_value = iter([("Red Apple", 1.0)])
    client = _index(redis=redis, click_buffer=click_buffer)

    with patch.object(client, "rescore") as mock_rescore:
        client.flush()

    click_buffer.flush.assert_called_once()
    mock_rescore.assert_not_called()
    redis.zincrby.assert_called_once_with("ac:vocabulary", 1.0, "red apple")
    redis.zscore.assert_called_once_with("ac:vocabulary", "red apple")
    assert redis.zadd.call_count == 8
    assert redis.zremrangebyrank.call_count == 8
    redis.pipeline.assert_not_called()


def test_flush_with_empty_click_buffer():
    redis = Mock()
    click_buffer = Mock(spec=RedisClickBuffer)
    click_buffer.flush.return_value = iter([])
    client = _index(redis=redis, click_buffer=click_buffer)

    client.flush()

    click_buffer.flush.assert_called_once()
    redis.zincrby.assert_not_called()
    redis.zscore.assert_not_called()
    redis.zadd.assert_not_called()
    redis.zremrangebyrank.assert_not_called()
    redis.pipeline.assert_not_called()


def test_flush_negative_delta_rebuilds_prefix():
    redis = Mock()
    redis.zscore.return_value = -2.0
    redis.zmscore.return_value = [5.0]
    redis.zrange.return_value = ["cherry"]
    click_buffer = Mock(spec=RedisClickBuffer)
    click_buffer.flush.return_value = iter([("Apple", -3.0)])
    pipe = _mock_pipeline(redis)
    client = _index(redis=redis, click_buffer=click_buffer)

    with patch.object(client, "rescore") as mock_rescore:
        client.flush()

    click_buffer.flush.assert_called_once()
    mock_rescore.assert_not_called()
    redis.zincrby.assert_called_once_with("ac:vocabulary", -3.0, "apple")
    redis.zscore.assert_called_once_with("ac:vocabulary", "apple")
    assert redis.zadd.call_count == 5
    assert redis.zmscore.call_count == 5
    assert redis.zrange.call_count == 5
    assert redis.pipeline.call_count == 5
    assert pipe.delete.call_count == 5
    assert pipe.zadd.call_count == 5
    redis.zremrangebyrank.assert_not_called()


def test_search_single_token_returns_normalized_text():
    redis = Mock()
    redis.zrevrange.return_value = [("apple", 1.0)]
    client = RedisScoredIndex(
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
    assert results == [("apple", 1.0, {"category": "fruit"})]


def test_search_multi_token_uses_zinterstore():
    redis = Mock()
    redis.zrevrange.return_value = [("red apple", 2.0)]
    client = RedisScoredIndex(
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
    assert results == [("red apple", 2.0, {})]


def test_search_returns_empty_for_empty_query():
    redis = Mock()
    client = _index(redis=redis)

    results = client.search("   ")

    assert results == []
    redis.zrevrange.assert_not_called()


def test_create_redis_scored_index_wires_components():
    redis = Mock()
    client = create_redis_scored_index("ac", redis)

    assert isinstance(client, RedisScoredIndex)
    assert client.name == "ac"
    assert client.redis is redis
    assert isinstance(client.normalizer, NoopNormalizer)
    assert isinstance(client.tokenizer, NoopTokenizer)
    assert isinstance(client.metadata_storage, RedisMetadataStorage)
    assert isinstance(client.click_buffer, RedisClickBuffer)
    assert client.top_n == 5
