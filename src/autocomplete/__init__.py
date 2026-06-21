"""Autocomplete library."""

from autocomplete.clients import Client
from autocomplete.normalizers import LowercaseNormalizer, Normalizer
from autocomplete.prototypes import ModulePrototype, SimpleTrie
from autocomplete.tokenizers import NoSplitTokenizer, Tokenizer, WhitespaceTokenizer

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Client",
    "ModulePrototype",
    "SimpleTrie",
    "Normalizer",
    "LowercaseNormalizer",
    "Tokenizer",
    "NoSplitTokenizer",
    "WhitespaceTokenizer",
]
