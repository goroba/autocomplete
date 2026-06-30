import pytest
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from autocomplete.factories import create_sqlalchemy_scored_index
from autocomplete.indexer import SqlAlchemyOrmTableIndexer
from autocomplete.metadata import SqlAlchemyMetadataStorage
from autocomplete.normalizers import LowercaseNormalizer
from autocomplete.schemas.sqlalchemy import create_tables
from autocomplete.tokenizers import WhitespaceTokenizer


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "catalog_items"
    label: Mapped[str] = mapped_column(primary_key=True)
    weight: Mapped[float] = mapped_column()
    category: Mapped[str] = mapped_column()


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    create_tables(eng)
    return eng


def _index(engine, name="ac"):
    return create_sqlalchemy_scored_index(
        name,
        engine,
        normalizer=LowercaseNormalizer(),
        tokenizer=WhitespaceTokenizer(),
        metadata_storage=SqlAlchemyMetadataStorage(name, engine),
    )


def test_sqlalchemy_orm_table_indexer_populates_index(engine):
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            insert(Item.__table__),
            [
                {"label": "Apple", "weight": 10.0, "category": "fruit"},
                {"label": "Apricot", "weight": 20.0, "category": "fruit"},
            ],
        )

    index = _index(engine)
    indexer = SqlAlchemyOrmTableIndexer(
        engine,
        Item,
        text_column="label",
        score_column="weight",
    )

    count = indexer.populate(index)

    assert count == 2
    results = index.search("ap")
    assert len(results) == 2
    assert results[0][0] == "apricot"
    assert results[1][0] == "apple"
