from sqlalchemy import Column, Float, MetaData, String, Table, create_engine

from autocomplete.factories import (
    create_sqlalchemy_orm_table_index,
    create_sqlalchemy_table_index,
)
from autocomplete.indexes import SqlAlchemyTableIndex
from autocomplete.metadata import SqlAlchemyMetadataStorage
from autocomplete.click_buffers import SqlAlchemyClickBuffer
from autocomplete.normalizers import NoopNormalizer
from autocomplete.tokenizers import NoopTokenizer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


metadata = MetaData()

items_table = Table(
    "items",
    metadata,
    Column("label", String, primary_key=True),
    Column("weight", Float),
)


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"
    label: Mapped[str] = mapped_column(primary_key=True)
    weight: Mapped[float] = mapped_column()


def test_create_sqlalchemy_table_index_returns_index():
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)

    client = create_sqlalchemy_table_index(
        "items-ac",
        engine,
        items_table,
        text_column="label",
        score_column="weight",
    )

    assert isinstance(client, SqlAlchemyTableIndex)
    assert client.name == "items-ac"
    assert client.engine is engine
    assert isinstance(client.normalizer, NoopNormalizer)
    assert isinstance(client.tokenizer, NoopTokenizer)
    assert isinstance(client.metadata_storage, SqlAlchemyMetadataStorage)
    assert isinstance(client.click_buffer, SqlAlchemyClickBuffer)


def test_create_sqlalchemy_orm_table_index_returns_index():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    client = create_sqlalchemy_orm_table_index(
        "items-ac",
        engine,
        Item,
        text_field="label",
        score_field="weight",
    )

    assert isinstance(client, SqlAlchemyTableIndex)
    assert client.name == "items-ac"
    assert client.text_column.key == "label"
    assert client.score_column.key == "weight"
