from __future__ import annotations

from collections.abc import Iterator

from autocomplete.click_buffers.click_buffer import ClickBuffer
from autocomplete.clients.client import Client


class NoopClickBuffer(ClickBuffer):
    def __init__(self, *, click_rate: float = 1.0) -> None:
        self.click_rate = click_rate
        self.client: Client | None = None

    def set_client(self, client: Client) -> None:
        self.client = client

    def click_to_score(self, clicks: int) -> float:
        return clicks * self.click_rate

    def click(self, text: str, *, clicks: int = 1) -> None:
        self.client.rescore(text, self.click_to_score(clicks))

    def flush(self) -> Iterator[tuple[str, float]]:
        return iter(())
