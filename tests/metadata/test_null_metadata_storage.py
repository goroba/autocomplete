from autocomplete.metadata.metadata_storage import MetadataStorage
from autocomplete.metadata.null_metadata_storage import NullMetadataStorage


def test_null_metadata_storage_is_metadata_storage():
    assert isinstance(NullMetadataStorage(), MetadataStorage)


def test_get_returns_none():
    storage = NullMetadataStorage()
    assert storage.get("any_key") is None


def test_set_is_noop():
    storage = NullMetadataStorage()
    storage.set("key", {"score": 1})


def test_delete_is_noop():
    storage = NullMetadataStorage()
    storage.delete("key")
