from autocomplete.clients.client import Client
from autocomplete.normalizers.lowercase_normalizer import LowercaseNormalizer
from autocomplete.tokenizers.whitespace_tokenizer import WhitespaceTokenizer


class DummyClient(Client):
    def store(self, text, score=None, metadata=None):
        pass

    def search(self, query):
        return []

    def click(self, text, *, amount=None):
        pass

    def delete(self, text):
        pass


def test_client_stores_dependencies():
    normalizer = LowercaseNormalizer()
    tokenizer = WhitespaceTokenizer()

    client = DummyClient(normalizer=normalizer, tokenizer=tokenizer)

    assert client.normalizer is normalizer
    assert client.tokenizer is tokenizer
    assert client.top_n == 5
    assert client.min_query_length == 1


def test_client_accepts_custom_top_n():
    client = DummyClient(
        normalizer=LowercaseNormalizer(),
        tokenizer=WhitespaceTokenizer(),
        top_n=10,
    )

    assert client.top_n == 10
