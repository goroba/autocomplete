from autocomplete.tokenizers.whitespace_tokenizer import WhitespaceTokenizer


def test_whitespace_tokenizer_splits_words():
    tokenizer = WhitespaceTokenizer()
    assert tokenizer.tokenize("one two") == ["one", "two"]


def test_whitespace_tokenizer_collapses_multiple_spaces():
    tokenizer = WhitespaceTokenizer()
    assert tokenizer.tokenize("one   two") == ["one", "two"]


def test_whitespace_tokenizer_splits_on_tabs_and_newlines():
    tokenizer = WhitespaceTokenizer()
    assert tokenizer.tokenize("one\ttwo\nthree") == ["one", "two", "three"]


def test_whitespace_tokenizer_empty_string():
    tokenizer = WhitespaceTokenizer()
    assert tokenizer.tokenize("") == []
