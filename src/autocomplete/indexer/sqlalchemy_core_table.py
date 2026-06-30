from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.engine import Row
from sqlalchemy.sql.schema import Column

from autocomplete.indexer.indexer import Indexer
from autocomplete.indexes import Index

if TYPE_CHECKING:
    from sqlalchemy import ColumnElement
    from sqlalchemy.engine import Engine
    from sqlalchemy.sql.schema import Table


class SqlAlchemyCoreTableIndexer(Indexer):
    def __init__(
        self,
        engine: Engine,
        table: Table,
        *,
        text_column: str | Column[Any],
        score_column: str | Column[Any] | None = None,
        metadata_fn: Callable[[Row[Any]], dict[str, Any]] | None = None,
        where: ColumnElement[bool] | None = None,
    ) -> None:
        self.engine = engine
        self.table = table
        self.text_column = self._resolve_column(text_column)
        self.score_column = (
            self._resolve_column(score_column) if score_column is not None else None
        )
        self.metadata_fn = metadata_fn
        self.where = where

    def _resolve_column(self, column: str | Column[Any]) -> Column[Any]:
        if isinstance(column, str):
            return self.table.c[column]
        return column

    def populate(self, index: Index) -> int:
        stmt = select(self.table)
        if self.where is not None:
            stmt = stmt.where(self.where)

        count = 0
        with self.engine.connect() as conn:
            for row in conn.execute(stmt):
                mapping = row._mapping
                text = mapping[self.text_column.key]
                score = (
                    float(mapping[self.score_column.key])
                    if self.score_column is not None
                    else None
                )
                metadata = self.metadata_fn(row) if self.metadata_fn is not None else None
                index.store(text, score=score, metadata=metadata)
                count += 1

        return count
