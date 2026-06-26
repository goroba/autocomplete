from autocomplete.indexes import Index


class DummyIndex(Index):
    def store(self, text, score=None, metadata=None):
        pass

    def search(self, query):
        return []

    def click(self, text, *, clicks=1):
        pass

    def rescore(self, text, score):
        pass

    def delete(self, text):
        pass

    def flush(self):
        pass


def test_index_can_be_instantiated():
    index = DummyIndex()

    assert isinstance(index, Index)


def test_index_implements_interface():
    index = DummyIndex()

    index.store("hello", score=1.0)
    assert index.search("hel") == []
    index.click("hello")
    index.rescore("hello", 1.0)
    index.delete("hello")
    index.flush()
