import pytest
from sqlalchemy import create_engine, select

from autocomplete.click_buffers import NoopClickBuffer, SqlAlchemyClickBuffer
from autocomplete.factories import create_sqlalchemy_scored_index
from autocomplete.indexes import SqlAlchemyScoredIndex
from autocomplete.metadata import NullMetadataStorage, SqlAlchemyMetadataStorage
from autocomplete.normalizers import LowercaseNormalizer, NoopNormalizer
from autocomplete.schemas.sqlalchemy import (
    create_index_tables,
    create_tables,
    prefix_table,
    vocabulary_table,
)
from autocomplete.tokenizers import NoopTokenizer, WhitespaceTokenizer


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    create_tables(eng)
    return eng


def _index(engine, **kwargs) -> SqlAlchemyScoredIndex:
    name = kwargs.pop("name", "ac")
    return SqlAlchemyScoredIndex(
        name,
        engine,
        normalizer=LowercaseNormalizer(),
        tokenizer=WhitespaceTokenizer(),
        **kwargs,
    )


def test_sqlalchemy_scored_index_stores_dependencies(engine):
    normalizer = LowercaseNormalizer()
    tokenizer = WhitespaceTokenizer()

    client = SqlAlchemyScoredIndex(
        "ac",
        engine,
        normalizer=normalizer,
        tokenizer=tokenizer,
    )

    assert client.name == "ac"
    assert client.engine is engine
    assert client.normalizer is normalizer
    assert client.tokenizer is tokenizer
    assert client.top_n == 5
    assert isinstance(client.metadata_storage, NullMetadataStorage)
    assert isinstance(client.click_buffer, NoopClickBuffer)


def test_store_adds_to_vocabulary_and_prefix(engine):
    client = _index(engine)

    client.store("Apple")

    with engine.connect() as conn:
        vocab_score = conn.execute(
            select(vocabulary_table.c.score).where(
                vocabulary_table.c.index_name == "ac",
                vocabulary_table.c.text == "apple",
            )
        ).scalar_one()
        assert vocab_score == 0

        prefixes = conn.execute(
            select(prefix_table.c.prefix).where(
                prefix_table.c.index_name == "ac",
                prefix_table.c.text == "apple",
            )
        ).scalars().all()
        assert sorted(prefixes) == ["a", "ap", "app", "appl", "apple"]


def test_store_does_not_trim_vocabulary(engine):
    client = _index(engine)

    for i in range(10):
        client.store(f"item{i}")

    with engine.connect() as conn:
        count = conn.execute(
            select(vocabulary_table.c.text).where(
                vocabulary_table.c.index_name == "ac",
            )
        ).all()
        assert len(count) == 10


def test_trim_keeps_only_top_n_per_prefix(engine):
    client = _index(engine, top_n=2)

    client.store("apple", score=10.0)
    client.store("apricot", score=20.0)
    client.store("application", score=30.0)

    with engine.connect() as conn:
        rows = conn.execute(
            select(prefix_table.c.text, prefix_table.c.score).where(
                prefix_table.c.index_name == "ac",
                prefix_table.c.prefix == "ap",
            )
            .order_by(prefix_table.c.score.desc())
        ).all()
        assert len(rows) == 2
        assert rows[0].text == "application"
        assert rows[1].text == "apricot"


def test_search_single_token_returns_top_n_by_score(engine):
    client = _index(engine, metadata_storage=SqlAlchemyMetadataStorage("ac", engine))

    client.store("apple", score=10.0, metadata={"category": "fruit"})
    client.store("apricot", score=20.0)
    client.store("application", score=30.0)

    results = client.search("app")

    assert len(results) == 2
    assert results[0] == ("application", 30.0, {})
    assert results[1] == ("apple", 10.0, {"category": "fruit"})


def test_search_multi_token_intersects_prefix_sets(engine):
    client = _index(engine)

    client.store("red apple", score=10.0)
    client.store("red berry", score=20.0)
    client.store("green apple", score=30.0)

    results = client.search("red app")

    assert len(results) == 1
    assert results[0][0] == "red apple"
    assert results[0][1] == 10.0


def test_search_returns_empty_for_empty_query(engine):
    client = _index(engine)

    results = client.search("   ")

    assert results == []


def test_store_and_search_with_index_tables_only():
    eng = create_engine("sqlite:///:memory:")
    create_index_tables(eng)
    client = SqlAlchemyScoredIndex(
        "ac",
        eng,
        normalizer=LowercaseNormalizer(),
        tokenizer=WhitespaceTokenizer(),
        metadata_storage=NullMetadataStorage(),
        click_buffer=NoopClickBuffer(),
    )

    client.store("hello world", score=1.0)
    results = client.search("hel")

    assert results == [("hello world", 1.0, {})]


def test_rescore_positive_updates_scores(engine):
    client = _index(engine)

    client.store("Apple", score=1.0)
    client.rescore("Apple", 2.0)

    with engine.connect() as conn:
        score = conn.execute(
            select(vocabulary_table.c.score).where(
                vocabulary_table.c.index_name == "ac",
                vocabulary_table.c.text == "apple",
            )
        ).scalar_one()
        assert score == 3.0

        prefix_score = conn.execute(
            select(prefix_table.c.score).where(
                prefix_table.c.index_name == "ac",
                prefix_table.c.prefix == "apple",
                prefix_table.c.text == "apple",
            )
        ).scalar_one()
        assert prefix_score == 3.0


def test_rescore_negative_rebuilds_prefix_set(engine):
    client = _index(engine, top_n=2)

    client.store("apple", score=10.0)
    client.store("apricot", score=20.0)
    client.store("application", score=30.0)
    client.rescore("application", -25.0)

    with engine.connect() as conn:
        rows = conn.execute(
            select(prefix_table.c.text, prefix_table.c.score).where(
                prefix_table.c.index_name == "ac",
                prefix_table.c.prefix == "ap",
            )
            .order_by(prefix_table.c.score.desc())
        ).all()
        assert len(rows) == 2
        texts = [row.text for row in rows]
        assert "application" not in texts
        assert "apricot" in texts


def test_flush_applies_click_buffer(engine):
    client = _index(engine, click_buffer=SqlAlchemyClickBuffer("ac", engine))

    client.store("Red Apple", score=1.0)
    client.click("Red Apple", clicks=2)
    client.flush()

    with engine.connect() as conn:
        score = conn.execute(
            select(vocabulary_table.c.score).where(
                vocabulary_table.c.index_name == "ac",
                vocabulary_table.c.text == "red apple",
            )
        ).scalar_one()
        assert score == 3.0


def test_flush_with_empty_click_buffer(engine):
    client = _index(engine, click_buffer=NoopClickBuffer())

    client.store("Apple", score=1.0)
    client.flush()

    with engine.connect() as conn:
        score = conn.execute(
            select(vocabulary_table.c.score).where(
                vocabulary_table.c.index_name == "ac",
                vocabulary_table.c.text == "apple",
            )
        ).scalar_one()
        assert score == 1.0


def test_delete_removes_all_rows(engine):
    client = create_sqlalchemy_scored_index("ac", engine)

    client.store("Red Apple", score=1.0, metadata={"id": 1})
    client.delete("Red Apple")

    with engine.connect() as conn:
        vocab = conn.execute(
            select(vocabulary_table.c.text).where(
                vocabulary_table.c.index_name == "ac",
            )
        ).all()
        assert vocab == []

        prefixes = conn.execute(
            select(prefix_table.c.text).where(
                prefix_table.c.index_name == "ac",
                prefix_table.c.text == "red apple",
            )
        ).all()
        assert prefixes == []

    results = client.search("red")
    assert results == []


def test_metadata_round_trip(engine):
    client = create_sqlalchemy_scored_index("ac", engine)

    client.store("hello", score=1.0, metadata={"id": 42, "tag": "greeting"})
    results = client.search("hel")

    assert results == [("hello", 1.0, {"id": 42, "tag": "greeting"})]


def test_create_sqlalchemy_scored_index_wires_components(engine):
    client = create_sqlalchemy_scored_index("ac", engine)

    assert isinstance(client, SqlAlchemyScoredIndex)
    assert client.name == "ac"
    assert client.engine is engine
    assert isinstance(client.normalizer, NoopNormalizer)
    assert isinstance(client.tokenizer, NoopTokenizer)
    assert isinstance(client.metadata_storage, SqlAlchemyMetadataStorage)
    assert isinstance(client.click_buffer, SqlAlchemyClickBuffer)
    assert client.top_n == 5
