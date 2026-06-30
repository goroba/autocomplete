from __future__ import annotations

from typing import TYPE_CHECKING

from autocomplete.click_buffers import ClickBuffer, SqlAlchemyClickBuffer
from autocomplete.indexes import SqlAlchemyScoredIndex
from autocomplete.metadata import MetadataStorage, SqlAlchemyMetadataStorage
from autocomplete.normalizers import Normalizer
from autocomplete.tokenizers import Tokenizer

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


def create_sqlalchemy_scored_index(
    name: str,
    engine: Engine,
    *,
    top_n: int = 5,
    trim: bool = True,
    normalizer: Normalizer | None = None,
    tokenizer: Tokenizer | None = None,
    metadata_storage: MetadataStorage | None = None,
    click_buffer: ClickBuffer | None = None,
) -> SqlAlchemyScoredIndex:
    return SqlAlchemyScoredIndex(
        name,
        engine,
        top_n=top_n,
        trim=trim,
        normalizer=normalizer,
        tokenizer=tokenizer,
        metadata_storage=metadata_storage
        or SqlAlchemyMetadataStorage(name, engine),
        click_buffer=click_buffer or SqlAlchemyClickBuffer(name, engine),
    )
