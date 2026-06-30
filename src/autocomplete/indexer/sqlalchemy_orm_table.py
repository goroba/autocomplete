from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.engine import Row

from autocomplete.indexer.sqlalchemy_core_table import SqlAlchemyCoreTableIndexer

if TYPE_CHECKING:
    from sqlalchemy import ColumnElement
    from sqlalchemy.engine import Engine


class SqlAlchemyOrmTableIndexer(SqlAlchemyCoreTableIndexer):
    def __init__(
        self,
        engine: Engine,
        model: type[Any],
        *,
        text_column: str,
        score_column: str | None = None,
        metadata_fn: Callable[[Row[Any]], dict[str, Any]] | None = None,
        where: ColumnElement[bool] | None = None,
    ) -> None:
        mapper = sa_inspect(model)
        text_col = mapper.columns[text_column]
        score_col = mapper.columns[score_column] if score_column is not None else None
        super().__init__(
            engine,
            mapper.local_table,
            text_column=text_col,
            score_column=score_col,
            metadata_fn=metadata_fn,
            where=where,
        )
