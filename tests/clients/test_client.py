from autocomplete.clients.client import Client
from autocomplete.normalizers.lowercase_normalizer import LowercaseNormalizer
from autocomplete.tokenizers.whitespace_tokenizer import WhitespaceTokenizer


class DummyClient(Client):
    pass


def test_client_stores_dependencies():
    normalizer = LowercaseNormalizer()
    tokenizer = WhitespaceTokenizer()

    client = DummyClient(normalizer=normalizer, tokenizer=tokenizer)

    assert client.normalizer is normalizer
    assert client.tokenizer is tokenizer
    assert client.top_n == 5


def test_client_accepts_custom_top_n():
    client = DummyClient(
        normalizer=LowercaseNormalizer(),
        tokenizer=WhitespaceTokenizer(),
        top_n=10,
    )

    assert client.top_n == 10
