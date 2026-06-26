from unittest.mock import Mock, call

from autocomplete.click_buffers import RedisClickBuffer


def _buffer(**kwargs) -> RedisClickBuffer:
    redis = kwargs.pop("redis", Mock())
    name = kwargs.pop("name", "ac")
    return RedisClickBuffer(name, redis, **kwargs)


def test_redis_click_buffer_stores_dependencies():
    redis = Mock()
    buffer = RedisClickBuffer("ac", redis, click_rate=0.5)

    assert buffer.name == "ac"
    assert buffer.redis is redis
    assert buffer.click_rate == 0.5


def test_click_buffers_clicks_in_sorted_set():
    redis = Mock()
    buffer = _buffer(redis=redis)

    buffer.click("Red Apple")

    redis.zincrby.assert_called_once_with("ac:click_buffer", 1.0, "Red Apple")


def test_click_to_score_scales_clicks_by_click_rate():
    buffer = _buffer(click_rate=0.5)

    assert buffer.click_to_score(2) == 1.0
    assert buffer.click_to_score(1) == 0.5


def test_click_uses_custom_amount():
    redis = Mock()
    buffer = _buffer(redis=redis)

    buffer.click("Red Apple", clicks=3)

    redis.zincrby.assert_called_once_with("ac:click_buffer", 3.0, "Red Apple")


def test_flush_yields_buffered_pairs_and_clears_buffer():
    redis = Mock()
    redis.zpopmax.side_effect = [
        [("Red Apple", 2.0), ("Banana", 1.0)],
        [],
    ]
    buffer = _buffer(redis=redis)

    pairs = list(buffer.flush())

    assert redis.zpopmax.call_args_list == [
        call("ac:click_buffer", count=10),
        call("ac:click_buffer", count=10),
    ]
    assert pairs == [("Red Apple", 2.0), ("Banana", 1.0)]


def test_flush_fetches_in_batches():
    redis = Mock()
    redis.zpopmax.side_effect = [
        [("A", 1.0), ("B", 2.0)],
        [("C", 3.0)],
        [],
    ]
    buffer = _buffer(redis=redis, flush_batch_size=2)

    pairs = list(buffer.flush())

    assert redis.zpopmax.call_args_list == [
        call("ac:click_buffer", count=2),
        call("ac:click_buffer", count=2),
        call("ac:click_buffer", count=2),
    ]
    assert pairs == [("A", 1.0), ("B", 2.0), ("C", 3.0)]


def test_flush_returns_empty_when_buffer_empty():
    redis = Mock()
    redis.zpopmax.return_value = []
    buffer = _buffer(redis=redis)

    pairs = list(buffer.flush())

    redis.zpopmax.assert_called_once_with("ac:click_buffer", count=10)
    assert pairs == []


def test_second_flush_returns_empty():
    redis = Mock()
    redis.zpopmax.side_effect = [[("Red Apple", 1.0)], [], []]
    buffer = _buffer(redis=redis)

    list(buffer.flush())
    pairs = list(buffer.flush())

    assert pairs == []


def test_iter_yields_buffered_pairs_without_removing():
    redis = Mock()
    redis.zrange.return_value = [("Red Apple", 2.0), ("Banana", 1.0)]
    buffer = _buffer(redis=redis)

    pairs = list(buffer)

    redis.zrange.assert_called_once_with("ac:click_buffer", 0, 9, withscores=True)
    redis.zpopmax.assert_not_called()
    assert pairs == [("Red Apple", 2.0), ("Banana", 1.0)]


def test_iter_fetches_in_batches():
    redis = Mock()
    redis.zrange.side_effect = [
        [("A", 1.0), ("B", 2.0)],
        [("C", 3.0)],
    ]
    buffer = _buffer(redis=redis, flush_batch_size=2)

    pairs = list(buffer)

    assert redis.zrange.call_args_list == [
        call("ac:click_buffer", 0, 1, withscores=True),
        call("ac:click_buffer", 2, 3, withscores=True),
    ]
    redis.zpopmax.assert_not_called()
    assert pairs == [("A", 1.0), ("B", 2.0), ("C", 3.0)]


def test_iter_returns_empty_when_buffer_empty():
    redis = Mock()
    redis.zrange.return_value = []
    buffer = _buffer(redis=redis)

    pairs = list(buffer)

    redis.zrange.assert_called_once_with("ac:click_buffer", 0, 9, withscores=True)
    redis.zpopmax.assert_not_called()
    assert pairs == []
