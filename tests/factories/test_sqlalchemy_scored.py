import pytest
from sqlalchemy import create_engine

from autocomplete.click_buffers import SqlAlchemyClickBuffer
from autocomplete.factories import create_sqlalchemy_scored_index
from autocomplete.indexes import SqlAlchemyScoredIndex
from autocomplete.metadata import SqlAlchemyMetadataStorage
from autocomplete.normalizers import NoopNormalizer
from autocomplete.schemas.sqlalchemy import create_tables
from autocomplete.tokenizers import NoopTokenizer


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    create_tables(eng)
    return eng


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
