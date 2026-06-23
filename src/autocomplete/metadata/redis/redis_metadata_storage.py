from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autocomplete.metadata import MetadataStorage

if TYPE_CHECKING:
    from redis import Redis


class RedisMetadataStorage(MetadataStorage):
    def __init__(self, prefix: str, redis: Redis) -> None:
        self.name = prefix
        self.redis = redis

    def _metadata_key(self, key: str) -> str:
        return f"{self.name}:metadata:{key}"

    def get(self, key: str) -> dict[str, Any] | None:
        result = self.redis.hgetall(self._metadata_key(key))
        if not result:
            return None
        return result

    def set(self, key: str, metadata: dict[str, Any]) -> None:
        self.redis.hset(self._metadata_key(key), mapping=metadata)
    
    def delete(self, key: str) -> None:
        self.redis.hdel(self._metadata_key(key))
