from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Column, Float, Index, MetaData, String, Table
from sqlalchemy.types import JSON

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection, Engine
    from sqlalchemy.sql import Insert

index_metadata = MetaData()

vocabulary_table = Table(
    "autocomplete_vocabulary",
    index_metadata,
    Column("index_name", String, primary_key=True),
    Column("text", String, primary_key=True),
    Column("score", Float, nullable=False, server_default="0"),
)

prefix_table = Table(
    "autocomplete_prefix",
    index_metadata,
    Column("index_name", String, primary_key=True),
    Column("prefix", String, primary_key=True),
    Column("text", String, primary_key=True),
    Column("score", Float, nullable=False, server_default="0"),
)

Index(
    "ix_autocomplete_prefix_lookup",
    prefix_table.c.index_name,
    prefix_table.c.prefix,
    prefix_table.c.score.desc(),
)

metadata_storage_metadata = MetaData()

metadata_table = Table(
    "autocomplete_metadata",
    metadata_storage_metadata,
    Column("index_name", String, primary_key=True),
    Column("text", String, primary_key=True),
    Column("metadata", JSON, nullable=True),
)

click_buffer_metadata = MetaData()

click_buffer_table = Table(
    "autocomplete_click_buffer",
    click_buffer_metadata,
    Column("index_name", String, primary_key=True),
    Column("text", String, primary_key=True),
    Column("score", Float, nullable=False, server_default="0"),
)


def dialect_insert(conn: Connection, table: Table) -> Insert:
    if conn.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as insert_fn
    elif conn.dialect.name == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as insert_fn
    else:
        raise NotImplementedError(
            f"Upsert is not supported for dialect {conn.dialect.name!r}"
        )
    return insert_fn(table)


def create_index_tables(engine: Engine) -> None:
    index_metadata.create_all(engine)


def drop_index_tables(engine: Engine) -> None:
    index_metadata.drop_all(engine)


def create_metadata_tables(engine: Engine) -> None:
    metadata_storage_metadata.create_all(engine)


def drop_metadata_tables(engine: Engine) -> None:
    metadata_storage_metadata.drop_all(engine)


def create_click_buffer_tables(engine: Engine) -> None:
    click_buffer_metadata.create_all(engine)


def drop_click_buffer_tables(engine: Engine) -> None:
    click_buffer_metadata.drop_all(engine)


def create_tables(engine: Engine) -> None:
    create_index_tables(engine)
    create_metadata_tables(engine)
    create_click_buffer_tables(engine)


def drop_tables(engine: Engine) -> None:
    drop_click_buffer_tables(engine)
    drop_metadata_tables(engine)
    drop_index_tables(engine)
