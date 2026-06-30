from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.sql.schema import Column

from autocomplete.click_buffers import ClickBuffer, SqlAlchemyClickBuffer
from autocomplete.indexes import SqlAlchemyTableIndex
from autocomplete.metadata import MetadataStorage, SqlAlchemyMetadataStorage
from autocomplete.normalizers import Normalizer
from autocomplete.tokenizers import Tokenizer

if TYPE_CHECKING:
    from sqlalchemy import ColumnElement
    from sqlalchemy.engine import Engine
    from sqlalchemy.sql.schema import Column, Table


def create_sqlalchemy_table_index(
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
) -> SqlAlchemyTableIndex:
    return SqlAlchemyTableIndex(
        name,
        engine,
        table,
        text_column=text_column,
        score_column=score_column,
        top_n=top_n,
        where=where,
        normalizer=normalizer,
        tokenizer=tokenizer,
        metadata_storage=metadata_storage
        or SqlAlchemyMetadataStorage(name, engine),
        click_buffer=click_buffer or SqlAlchemyClickBuffer(name, engine),
    )


def create_sqlalchemy_orm_table_index(
    name: str,
    engine: Engine,
    model: type[Any],
    *,
    text_field: str,
    score_field: str | None = None,
    top_n: int = 5,
    where: ColumnElement[bool] | None = None,
    normalizer: Normalizer | None = None,
    tokenizer: Tokenizer | None = None,
    metadata_storage: MetadataStorage | None = None,
    click_buffer: ClickBuffer | None = None,
) -> SqlAlchemyTableIndex:
    mapper = sa_inspect(model)
    table = mapper.local_table
    text_column = mapper.columns[text_field]
    score_column = mapper.columns[score_field] if score_field is not None else None

    return SqlAlchemyTableIndex(
        name,
        engine,
        table,
        text_column=text_column,
        score_column=score_column,
        top_n=top_n,
        where=where,
        normalizer=normalizer,
        tokenizer=tokenizer,
        metadata_storage=metadata_storage
        or SqlAlchemyMetadataStorage(name, engine),
        click_buffer=click_buffer or SqlAlchemyClickBuffer(name, engine),
    )
