from autocomplete.engines import Engine


class DummyEngine(Engine):
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


def test_engine_can_be_instantiated():
    engine = DummyEngine()

    assert isinstance(engine, Engine)


def test_engine_implements_interface():
    engine = DummyEngine()

    engine.store("hello", score=1.0)
    assert engine.search("hel") == []
    engine.click("hello")
    engine.rescore("hello", 1.0)
    engine.delete("hello")
    engine.flush()
