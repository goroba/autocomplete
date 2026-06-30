import pytest
from sqlalchemy import Column, Float, MetaData, String, Table, create_engine, insert, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from autocomplete.click_buffers import NoopClickBuffer, SqlAlchemyClickBuffer
from autocomplete.factories import (
    create_sqlalchemy_orm_table_index,
    create_sqlalchemy_table_index,
)
from autocomplete.indexes import SqlAlchemyTableIndex
from autocomplete.metadata import NullMetadataStorage, SqlAlchemyMetadataStorage
from autocomplete.normalizers import LowercaseNormalizer, NoopNormalizer
from autocomplete.schemas.sqlalchemy import create_tables
from autocomplete.tokenizers import NoopTokenizer, WhitespaceTokenizer

metadata = MetaData()

products_table = Table(
    "products",
    metadata,
    Column("name", String, primary_key=True),
    Column("score", Float, nullable=False),
    Column("category", String, nullable=False),
)


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"
    name: Mapped[str] = mapped_column(primary_key=True)
    score: Mapped[float] = mapped_column()
    category: Mapped[str] = mapped_column()


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    metadata.create_all(eng)
    return eng


def _seed_products(engine):
    rows = [
        {"name": "apple", "score": 10.0, "category": "fruit"},
        {"name": "apricot", "score": 20.0, "category": "fruit"},
        {"name": "application", "score": 30.0, "category": "software"},
        {"name": "red apple", "score": 10.0, "category": "fruit"},
        {"name": "red berry", "score": 20.0, "category": "fruit"},
        {"name": "green apple", "score": 30.0, "category": "fruit"},
        {"name": "apple red", "score": 5.0, "category": "fruit"},
    ]
    with engine.begin() as conn:
        conn.execute(insert(products_table), rows)


def _index(engine, **kwargs) -> SqlAlchemyTableIndex:
    name = kwargs.pop("name", "ac")
    return SqlAlchemyTableIndex(
        name,
        engine,
        products_table,
        text_column="name",
        score_column="score",
        normalizer=LowercaseNormalizer(),
        tokenizer=WhitespaceTokenizer(),
        **kwargs,
    )


def test_sqlalchemy_table_index_stores_dependencies(engine):
    normalizer = LowercaseNormalizer()
    tokenizer = WhitespaceTokenizer()

    client = SqlAlchemyTableIndex(
        "ac",
        engine,
        products_table,
        text_column="name",
        score_column="score",
        normalizer=normalizer,
        tokenizer=tokenizer,
    )

    assert client.name == "ac"
    assert client.engine is engine
    assert client.table is products_table
    assert client.text_column is products_table.c.name
    assert client.score_column is products_table.c.score
    assert client.normalizer is normalizer
    assert client.tokenizer is tokenizer
    assert client.top_n == 5
    assert isinstance(client.metadata_storage, NullMetadataStorage)
    assert isinstance(client.click_buffer, NoopClickBuffer)


def test_search_single_token_returns_top_n_by_score(engine):
    _seed_products(engine)
    client = _index(engine, top_n=2)

    results = client.search("app")

    assert len(results) == 2
    assert results[0] == ("application", 30.0, {})
    assert results[1] == ("apple", 10.0, {})


def test_search_multi_token_matches_word_prefixes(engine):
    _seed_products(engine)
    client = _index(engine)

    results = client.search("red app")

    assert len(results) == 1
    assert results[0][0] == "red apple"
    assert results[0][1] == 10.0


def test_search_multi_token_does_not_match_reordered_words(engine):
    _seed_products(engine)
    client = _index(engine)

    results = client.search("red app")

    texts = [row[0] for row in results]
    assert "apple red" not in texts


def test_search_returns_empty_for_empty_query(engine):
    _seed_products(engine)
    client = _index(engine)

    results = client.search("   ")

    assert results == []


def test_search_without_score_column(engine):
    _seed_products(engine)
    client = SqlAlchemyTableIndex(
        "ac",
        engine,
        products_table,
        text_column="name",
        normalizer=LowercaseNormalizer(),
        tokenizer=WhitespaceTokenizer(),
    )

    results = client.search("app")

    assert len(results) == 3
    assert all(score == 0.0 for _, score, _ in results)
    texts = [text for text, _, _ in results]
    assert texts == sorted(texts)


def test_search_with_where_clause(engine):
    _seed_products(engine)
    client = _index(
        engine,
        where=products_table.c.category == "fruit",
        top_n=10,
    )

    results = client.search("app")

    assert len(results) == 2
    texts = [result[0] for result in results]
    assert texts == ["apple", "apple red"]
    assert all(result[0] != "application" for result in results)


def test_store_and_delete_are_noops(engine):
    _seed_products(engine)
    client = _index(engine)

    with engine.connect() as conn:
        before = conn.execute(select(products_table)).all()

    client.store("new item", score=99.0, metadata={"id": 1})
    client.delete("apple")

    with engine.connect() as conn:
        after = conn.execute(select(products_table)).all()

    assert before == after


def test_rescore_updates_user_table_score(engine):
    _seed_products(engine)
    client = _index(engine)

    client.rescore("apple", 2.0)

    with engine.connect() as conn:
        score = conn.execute(
            select(products_table.c.score).where(products_table.c.name == "apple")
        ).scalar_one()
        assert score == 12.0


def test_rescore_without_score_column_is_noop(engine):
    _seed_products(engine)
    client = SqlAlchemyTableIndex(
        "ac",
        engine,
        products_table,
        text_column="name",
        normalizer=LowercaseNormalizer(),
        tokenizer=WhitespaceTokenizer(),
    )

    client.rescore("apple", 2.0)

    with engine.connect() as conn:
        score = conn.execute(
            select(products_table.c.score).where(products_table.c.name == "apple")
        ).scalar_one()
        assert score == 10.0


def test_flush_applies_click_buffer(engine):
    create_tables(engine)
    _seed_products(engine)
    client = _index(engine, click_buffer=SqlAlchemyClickBuffer("ac", engine))

    client.click("apple", clicks=2)
    client.flush()

    with engine.connect() as conn:
        score = conn.execute(
            select(products_table.c.score).where(products_table.c.name == "apple")
        ).scalar_one()
        assert score == 12.0


def test_search_attaches_metadata_from_storage(engine):
    create_tables(engine)
    _seed_products(engine)
    client = _index(
        engine,
        metadata_storage=SqlAlchemyMetadataStorage("ac", engine),
    )
    client.metadata_storage.set("apple", {"id": 42})

    results = client.search("app")

    apple_result = next(result for result in results if result[0] == "apple")
    assert apple_result[2] == {"id": 42}


def test_create_sqlalchemy_table_index_wires_components(engine):
    client = create_sqlalchemy_table_index(
        "ac",
        engine,
        products_table,
        text_column="name",
        score_column="score",
    )

    assert isinstance(client, SqlAlchemyTableIndex)
    assert client.name == "ac"
    assert client.engine is engine
    assert isinstance(client.normalizer, NoopNormalizer)
    assert isinstance(client.tokenizer, NoopTokenizer)
    assert isinstance(client.metadata_storage, SqlAlchemyMetadataStorage)
    assert isinstance(client.click_buffer, SqlAlchemyClickBuffer)


def test_create_sqlalchemy_orm_table_index(engine):
    Base.metadata.create_all(engine)
    _seed_products(engine)

    client = create_sqlalchemy_orm_table_index(
        "ac",
        engine,
        Product,
        text_field="name",
        score_field="score",
        normalizer=LowercaseNormalizer(),
        tokenizer=WhitespaceTokenizer(),
        metadata_storage=NullMetadataStorage(),
    )

    assert isinstance(client, SqlAlchemyTableIndex)
    assert client.text_column.key == "name"
    assert client.score_column.key == "score"

    results = client.search("red app")
    assert len(results) == 1
    assert results[0][0] == "red apple"
