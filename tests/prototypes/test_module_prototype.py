from autocomplete.clients.client import Client
from autocomplete.normalizers.lowercase_normalizer import LowercaseNormalizer
from autocomplete.prototypes.module_prototype import ModulePrototype
from autocomplete.tokenizers.whitespace_tokenizer import WhitespaceTokenizer


class DummyClient(Client):
    def __init__(self) -> None:
        super().__init__(
            normalizer=LowercaseNormalizer(),
            tokenizer=WhitespaceTokenizer(),
        )
        self.stored: list[tuple[str, float | None, dict | None]] = []
        self.searched: list[str] = []
        self.deleted: list[str] = []
        self.clicked: list[str] = []

    def store(self, text, score=None, metadata=None):
        self.stored.append((text, score, metadata))

    def search(self, query):
        self.searched.append(query)
        return []

    def delete(self, text):
        self.deleted.append(text)

    def click(self, text, *, amount=None):
        self.clicked.append(text)


class DummyPrototype(ModulePrototype):
    def __init__(self, client: DummyClient) -> None:
        self._client = client

    @property
    def client(self) -> DummyClient:
        return self._client


def test_module_prototype_delegates_to_client():
    client = DummyClient()
    prototype = DummyPrototype(client)

    prototype.store("Hello", score=1.0, metadata={"k": "v"})
    prototype.search("Hel")
    prototype.click("Hello")
    prototype.delete("Hello")

    assert client.stored == [("Hello", 1.0, {"k": "v"})]
    assert client.searched == ["Hel"]
    assert client.clicked == ["Hello"]
    assert client.deleted == ["Hello"]
