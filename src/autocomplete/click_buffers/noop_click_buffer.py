from __future__ import annotations

from collections.abc import Iterator

from autocomplete.click_buffers import ClickBuffer
from autocomplete.engines import Engine


class NoopClickBuffer(ClickBuffer):
    def __init__(self, *, click_rate: float = 1.0) -> None:
        self.click_rate = click_rate
        self.engine: Engine | None = None

    def set_engine(self, engine: Engine) -> None:
        self.engine = engine

    def click_to_score(self, clicks: int) -> float:
        return clicks * self.click_rate

    def click(self, text: str, *, clicks: int = 1) -> None:
        self.engine.rescore(text, self.click_to_score(clicks))

    def flush(self) -> Iterator[tuple[str, float]]:
        return iter(())
