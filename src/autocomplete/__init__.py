"""Autocomplete library."""

from autocomplete.clients import Client
from autocomplete.normalizers import LowercaseNormalizer, NoopNormalizer, Normalizer
from autocomplete.prototypes import ModulePrototype, ScorelessTrie
from autocomplete.tokenizers import NoopTokenizer, Tokenizer, WhitespaceTokenizer

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Client",
    "ModulePrototype",
    "ScorelessTrie",
    "Normalizer",
    "LowercaseNormalizer",
    "NoopNormalizer",
    "Tokenizer",
    "NoopTokenizer",
    "WhitespaceTokenizer",
]
