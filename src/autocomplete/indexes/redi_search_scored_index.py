from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from autocomplete.click_buffers import ClickBuffer, NoopClickBuffer
from autocomplete.indexes import Index
from autocomplete.normalizers import NoopNormalizer, Normalizer

if TYPE_CHECKING:
    from redis import Redis

SUGADD_COMMAND = "FT.SUGADD"
SUGGET_COMMAND = "FT.SUGGET"
SUGDEL_COMMAND = "FT.SUGDEL"


class RediSearchScoredIndex(Index):
    def __init__(
        self,
        name: str,
        redis: Redis,
        *,
        top_n: int = 5,
        fuzzy: bool = False,
        normalizer: Normalizer | None = None,
        click_buffer: ClickBuffer | None = None,
    ) -> None:
        self.name = name
        self.redis = redis
        self.top_n = top_n
        self.fuzzy = fuzzy
        self.normalizer = normalizer or NoopNormalizer()
        self.click_buffer = click_buffer or NoopClickBuffer()
        self.suggestions_key = f"{self.name}:suggestions"

    def _sugadd(
        self,
        text: str,
        score: float,
        *,
        increment: bool = False,
        payload: str | None = None,
    ) -> None:
        args: list[Any] = [SUGADD_COMMAND, self.suggestions_key, text, score]
        if increment:
            args.append("INCR")
        if payload is not None:
            args.extend(["PAYLOAD", payload])
        self.redis.execute_command(*args)

    def _sugget(self, prefix: str) -> list[tuple[str, float, str | None]]:
        args: list[Any] = [
            SUGGET_COMMAND,
            self.suggestions_key,
            prefix,
            "MAX",
            self.top_n,
        ]
        if self.fuzzy:
            args.append("FUZZY")
        args.extend(["WITHSCORES", "WITHPAYLOADS"])

        result = self.redis.execute_command(*args)
        if not result:
            return []

        entries: list[tuple[str, float, str | None]] = []
        index = 0
        while index < len(result):
            raw_text = result[index]
            text = raw_text.decode() if isinstance(raw_text, bytes) else raw_text
            score = float(result[index + 1])
            raw_payload = result[index + 2]
            index += 3
            payload: str | None = None
            if raw_payload is not None:
                payload = (
                    raw_payload.decode()
                    if isinstance(raw_payload, bytes)
                    else raw_payload
                )
            entries.append((text, score, payload))

        return entries

    def store(
        self,
        text: str,
        *,
        score: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        normalized_text = self.normalizer.normalize(text)
        payload = json.dumps(metadata) if metadata is not None else None
        self._sugadd(
            normalized_text,
            score if score is not None else 0,
            payload=payload,
        )

    def search(self, query: str) -> list[tuple[str, float, dict[str, Any]]]:
        normalized_query = self.normalizer.normalize(query)
        if not normalized_query.strip():
            return []

        return [
            (text, score, json.loads(payload) if payload is not None else {})
            for text, score, payload in self._sugget(normalized_query)
        ]

    def click(self, text: str, *, clicks: int = 1) -> None:
        self.click_buffer.click(text, clicks=clicks)

    def rescore(self, text: str, delta_score: float) -> None:
        normalized_text = self.normalizer.normalize(text)
        self._sugadd(normalized_text, delta_score, increment=True)

    def flush(self) -> None:
        for text, delta_score in self.click_buffer.flush():
            normalized_text = self.normalizer.normalize(text)
            self._sugadd(normalized_text, delta_score, increment=True)

    def delete(self, text: str) -> None:
        normalized_text = self.normalizer.normalize(text)
        self.redis.execute_command(
            SUGDEL_COMMAND,
            self.suggestions_key,
            normalized_text,
        )
