import pytest
from sqlalchemy import Column, Float, MetaData, String, Table, create_engine, insert

from autocomplete.factories import create_sqlalchemy_scored_index
from autocomplete.indexer import SqlAlchemyCoreTableIndexer
from autocomplete.metadata import SqlAlchemyMetadataStorage
from autocomplete.normalizers import LowercaseNormalizer
from autocomplete.schemas.sqlalchemy import create_tables
from autocomplete.tokenizers import WhitespaceTokenizer

items_metadata = MetaData()

items_table = Table(
    "items",
    items_metadata,
    Column("label", String, primary_key=True),
    Column("weight", Float),
    Column("category", String),
)


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    create_tables(eng)
    items_metadata.create_all(eng)
    return eng


def _index(engine, name="ac"):
    return create_sqlalchemy_scored_index(
        name,
        engine,
        normalizer=LowercaseNormalizer(),
        tokenizer=WhitespaceTokenizer(),
        metadata_storage=SqlAlchemyMetadataStorage(name, engine),
    )


def _seed_items(engine):
    with engine.begin() as conn:
        conn.execute(
            insert(items_table),
            [
                {"label": "Apple", "weight": 10.0, "category": "fruit"},
                {"label": "Apricot", "weight": 20.0, "category": "fruit"},
                {"label": "Application", "weight": 30.0, "category": "software"},
            ],
        )


def test_sqlalchemy_core_table_indexer_populates_index(engine):
    _seed_items(engine)
    index = _index(engine)
    indexer = SqlAlchemyCoreTableIndexer(
        engine,
        items_table,
        text_column="label",
        score_column="weight",
    )

    count = indexer.populate(index)

    assert count == 3
    results = index.search("app")
    assert len(results) == 2
    assert results[0] == ("application", 30.0, {})
    assert results[1] == ("apple", 10.0, {})


def test_sqlalchemy_core_table_indexer_passes_metadata_from_row(engine):
    _seed_items(engine)
    index = _index(engine)
    indexer = SqlAlchemyCoreTableIndexer(
        engine,
        items_table,
        text_column="label",
        score_column="weight",
        metadata_fn=lambda row: {"category": row.category},
    )

    indexer.populate(index)

    results = index.search("app")
    assert results[0] == ("application", 30.0, {"category": "software"})
    assert results[1] == ("apple", 10.0, {"category": "fruit"})


def test_sqlalchemy_core_table_indexer_without_score_column(engine):
    _seed_items(engine)
    index = _index(engine)
    indexer = SqlAlchemyCoreTableIndexer(
        engine,
        items_table,
        text_column="label",
    )

    indexer.populate(index)

    results = index.search("apricot")
    assert results == [("apricot", 0.0, {})]


def test_sqlalchemy_core_table_indexer_respects_where_filter(engine):
    _seed_items(engine)
    index = _index(engine)
    indexer = SqlAlchemyCoreTableIndexer(
        engine,
        items_table,
        text_column="label",
        score_column="weight",
        where=items_table.c.category == "fruit",
    )

    count = indexer.populate(index)

    assert count == 2
    results = index.search("ap")
    assert len(results) == 2
    assert {row[0] for row in results} == {"apple", "apricot"}
