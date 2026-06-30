from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import ColumnElement, literal, or_, select, update
from sqlalchemy.sql.schema import Column

from autocomplete.click_buffers import ClickBuffer, NoopClickBuffer
from autocomplete.indexes import Index
from autocomplete.metadata import MetadataStorage, NullMetadataStorage
from autocomplete.normalizers import NoopNormalizer, Normalizer
from autocomplete.tokenizers import NoopTokenizer, Tokenizer

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine
    from sqlalchemy.sql.schema import Table


class SqlAlchemyTableIndex(Index):
    def __init__(
        self,
        name: str,
        engine: Engine,
        table: Table,
        *,
        text_column: str | Column[Any],
        score_column: str | Column[Any] | None = None,
        top_n: int = 5,
        where: ColumnElement[bool] | None = None,
        normalizer: Normalizer | None = None,
        tokenizer: Tokenizer | None = None,
        metadata_storage: MetadataStorage | None = None,
        click_buffer: ClickBuffer | None = None,
    ) -> None:
        self.name = name
        self.engine = engine
        self.table = table
        self.text_column = self._resolve_column(text_column)
        self.score_column = (
            self._resolve_column(score_column) if score_column is not None else None
        )
        self.top_n = top_n
        self.where = where
        self.normalizer = normalizer or NoopNormalizer()
        self.tokenizer = tokenizer or NoopTokenizer()
        self.metadata_storage = metadata_storage or NullMetadataStorage()
        self.click_buffer = click_buffer or NoopClickBuffer()

    def _resolve_column(self, column: str | Column[Any]) -> Column[Any]:
        if isinstance(column, str):
            return self.table.c[column]
        return column

    def _search_conditions(self, tokens: list[str]) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = []
        for index, token in enumerate(tokens):
            if index == 0:
                conditions.append(self.text_column.startswith(token))
            else:
                conditions.append(
                    or_(
                        self.text_column.like(f"% {token}%"),
                        self.text_column.like(f"%\t{token}%"),
                    )
                )
        if self.where is not None:
            conditions.append(self.where)
        return conditions

    def _apply_score_delta(self, normalized_text: str, delta_score: float) -> None:
        if self.score_column is None:
            return

        conditions = [self.text_column == normalized_text]
        if self.where is not None:
            conditions.append(self.where)

        with self.engine.begin() as conn:
            conn.execute(
                update(self.table)
                .where(*conditions)
                .values({self.score_column: self.score_column + delta_score})
            )

    def store(
        self,
        text: str,
        *,
        score: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        pass

    def search(self, query: str) -> list[tuple[str, float, dict[str, Any]]]:
        normalized_query = self.normalizer.normalize(query)
        tokens = self.tokenizer.tokenize(normalized_query)
        if not tokens:
            return []

        score_expr = (
            self.score_column if self.score_column is not None else literal(0.0)
        )
        stmt = (
            select(self.text_column, score_expr.label("score"))
            .where(*self._search_conditions(tokens))
            .limit(self.top_n)
        )
        if self.score_column is not None:
            stmt = stmt.order_by(self.score_column.desc())
        else:
            stmt = stmt.order_by(self.text_column.asc())

        with self.engine.connect() as conn:
            results = conn.execute(stmt).all()

        return [
            (row[0], float(row[1]), self.metadata_storage.get(row[0]) or {})
            for row in results
        ]

    def click(self, text: str, *, clicks: int = 1) -> None:
        self.click_buffer.click(text, clicks=clicks)

    def rescore(self, text: str, delta_score: float) -> None:
        normalized_text = self.normalizer.normalize(text)
        self._apply_score_delta(normalized_text, delta_score)

    def flush(self) -> None:
        for text, delta_score in self.click_buffer.flush():
            normalized_text = self.normalizer.normalize(text)
            self._apply_score_delta(normalized_text, delta_score)

    def delete(self, text: str) -> None:
        pass
