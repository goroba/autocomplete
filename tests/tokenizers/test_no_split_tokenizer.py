from autocomplete.tokenizers.no_split_tokenizer import NoSplitTokenizer


def test_no_split_tokenizer_returns_single_token():
    tokenizer = NoSplitTokenizer()
    assert tokenizer.tokenize("one two") == ["one two"]


def test_no_split_tokenizer_preserves_whitespace():
    tokenizer = NoSplitTokenizer()
    assert tokenizer.tokenize("one   two") == ["one   two"]


def test_no_split_tokenizer_empty_string():
    tokenizer = NoSplitTokenizer()
    assert tokenizer.tokenize("") == [""]
