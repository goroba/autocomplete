from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, select

from autocomplete.metadata import MetadataStorage
from autocomplete.schemas.sqlalchemy import dialect_insert, metadata_table

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


class SqlAlchemyMetadataStorage(MetadataStorage):
    def __init__(self, name: str, engine: Engine) -> None:
        self.name = name
        self.engine = engine

    def get(self, key: str) -> dict[str, Any] | None:
        with self.engine.connect() as conn:
            result = conn.execute(
                select(metadata_table.c.metadata).where(
                    metadata_table.c.index_name == self.name,
                    metadata_table.c.text == key,
                )
            ).scalar_one_or_none()
        if result is None:
            return None
        return result

    def set(self, key: str, metadata: dict[str, Any]) -> None:
        with self.engine.begin() as conn:
            stmt = (
                dialect_insert(conn, metadata_table)
                .values(index_name=self.name, text=key, metadata=metadata)
                .on_conflict_do_update(
                    index_elements=[
                        metadata_table.c.index_name,
                        metadata_table.c.text,
                    ],
                    set_={"metadata": metadata},
                )
            )
            conn.execute(stmt)

    def delete(self, key: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                delete(metadata_table).where(
                    metadata_table.c.index_name == self.name,
                    metadata_table.c.text == key,
                )
            )
