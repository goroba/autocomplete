"""Autocomplete library."""

from autocomplete.factories import (
    create_bidirectional_score_index,
    create_scoreless_index,
)
from autocomplete.indexes import Index
from autocomplete.normalizers import LowercaseNormalizer, NoopNormalizer, Normalizer
from autocomplete.tokenizers import NoopTokenizer, Tokenizer, WhitespaceTokenizer

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Index",
    "create_bidirectional_score_index",
    "create_scoreless_index",
    "Normalizer",
    "LowercaseNormalizer",
    "NoopNormalizer",
    "Tokenizer",
    "NoopTokenizer",
    "WhitespaceTokenizer",
]
