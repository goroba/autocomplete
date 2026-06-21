from unittest.mock import Mock

from autocomplete.metadata.redis.redis_metadata_storage import RedisMetadataStorage


def test_redis_metadata_storage_stores_dependencies():
    redis = Mock()
    storage = RedisMetadataStorage("ac", redis)

    assert storage.prefix == "ac"
    assert storage.redis is redis


def test_set_persists_metadata_hash():
    redis = Mock()
    storage = RedisMetadataStorage("ac", redis)

    storage.set("Hello", {"category": "greeting"})

    redis.hset.assert_called_once_with(
        "ac:metadata:Hello",
        mapping={"category": "greeting"},
    )


def test_get_returns_metadata_hash():
    redis = Mock()
    redis.hgetall.return_value = {"category": "greeting"}
    storage = RedisMetadataStorage("ac", redis)

    result = storage.get("Hello")

    redis.hgetall.assert_called_once_with("ac:metadata:Hello")
    assert result == {"category": "greeting"}


def test_get_returns_none_when_missing():
    redis = Mock()
    redis.hgetall.return_value = {}
    storage = RedisMetadataStorage("ac", redis)

    assert storage.get("Hello") is None
