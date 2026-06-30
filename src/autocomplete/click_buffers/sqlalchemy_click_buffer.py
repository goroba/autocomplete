from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from sqlalchemy import delete, select

from autocomplete.click_buffers import ClickBuffer
from autocomplete.schemas.sqlalchemy import click_buffer_table, dialect_insert

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


class SqlAlchemyClickBuffer(ClickBuffer):
    def __init__(
        self,
        name: str,
        engine: Engine,
        *,
        click_rate: float = 1.0,
        flush_batch_size: int = 10,
    ) -> None:
        self.name = name
        self.engine = engine
        self.click_rate = click_rate
        self.flush_batch_size = flush_batch_size

    def click_to_score(self, clicks: int) -> float:
        return clicks * self.click_rate

    def click(self, text: str, *, clicks: int = 1) -> None:
        delta = self.click_to_score(clicks)
        with self.engine.begin() as conn:
            stmt = (
                dialect_insert(conn, click_buffer_table)
                .values(index_name=self.name, text=text, score=delta)
                .on_conflict_do_update(
                    index_elements=[
                        click_buffer_table.c.index_name,
                        click_buffer_table.c.text,
                    ],
                    set_={"score": click_buffer_table.c.score + delta},
                )
            )
            conn.execute(stmt)

    def flush(self) -> Iterator[tuple[str, float]]:
        while True:
            with self.engine.begin() as conn:
                rows = conn.execute(
                    select(
                        click_buffer_table.c.text,
                        click_buffer_table.c.score,
                    )
                    .where(click_buffer_table.c.index_name == self.name)
                    .order_by(click_buffer_table.c.score.desc())
                    .limit(self.flush_batch_size)
                ).all()
                if not rows:
                    return
                texts = [row.text for row in rows]
                conn.execute(
                    delete(click_buffer_table).where(
                        click_buffer_table.c.index_name == self.name,
                        click_buffer_table.c.text.in_(texts),
                    )
                )
            yield from ((row.text, row.score) for row in rows)
            if len(rows) < self.flush_batch_size:
                return

    def __iter__(self) -> Iterator[tuple[str, float]]:
        offset = 0
        while True:
            with self.engine.connect() as conn:
                rows = conn.execute(
                    select(
                        click_buffer_table.c.text,
                        click_buffer_table.c.score,
                    )
                    .where(click_buffer_table.c.index_name == self.name)
                    .order_by(click_buffer_table.c.text)
                    .offset(offset)
                    .limit(self.flush_batch_size)
                ).all()
            if not rows:
                return
            yield from ((row.text, row.score) for row in rows)
            if len(rows) < self.flush_batch_size:
                return
            offset += self.flush_batch_size
