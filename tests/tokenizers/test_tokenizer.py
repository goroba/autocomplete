import pytest

from autocomplete.tokenizers.tokenizer import Tokenizer


def test_tokenizer_cannot_be_instantiated():
    with pytest.raises(TypeError):
        Tokenizer()
