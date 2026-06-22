from autocomplete.tokenizers.noop_tokenizer import NoopTokenizer


def test_noop_tokenizer_returns_single_token():
    tokenizer = NoopTokenizer()
    assert tokenizer.tokenize("one two") == ["one two"]


def test_noop_tokenizer_preserves_whitespace():
    tokenizer = NoopTokenizer()
    assert tokenizer.tokenize("one   two") == ["one   two"]


def test_noop_tokenizer_empty_string():
    tokenizer = NoopTokenizer()
    assert tokenizer.tokenize("") == [""]
