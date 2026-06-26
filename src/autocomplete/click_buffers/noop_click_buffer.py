from __future__ import annotations

from collections.abc import Iterator

from autocomplete.click_buffers import ClickBuffer


class NoopClickBuffer(ClickBuffer):
    def click_to_score(self, clicks: int) -> float:
        return 0.0

    def click(self, text: str, *, clicks: int = 1) -> None:
        pass

    def flush(self) -> Iterator[tuple[str, float]]:
        return iter(())

    def __iter__(self) -> Iterator[tuple[str, float]]:
        return iter(())
