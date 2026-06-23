"""Autocomplete library."""

from autocomplete.engines import Engine
from autocomplete.factories import create_cumulative_score_engine, create_scoreless_engine
from autocomplete.normalizers import LowercaseNormalizer, NoopNormalizer, Normalizer
from autocomplete.tokenizers import NoopTokenizer, Tokenizer, WhitespaceTokenizer

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Engine",
    "create_cumulative_score_engine",
    "create_scoreless_engine",
    "Normalizer",
    "LowercaseNormalizer",
    "NoopNormalizer",
    "Tokenizer",
    "NoopTokenizer",
    "WhitespaceTokenizer",
]
