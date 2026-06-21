import pytest

from autocomplete.metadata.metadata_storage import MetadataStorage


def test_metadata_storage_cannot_be_instantiated():
    with pytest.raises(TypeError):
        MetadataStorage()
