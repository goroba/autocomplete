"""Autocomplete library."""

from autocomplete.clients import Client
from autocomplete.normalizers import LowercaseNormalizer, NoopNormalizer, Normalizer
from autocomplete.prototypes import CumulativeScore, ModulePrototype, Scoreless
from autocomplete.tokenizers import NoopTokenizer, Tokenizer, WhitespaceTokenizer

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Client",
    "ModulePrototype",
    "CumulativeScore",
    "Scoreless",
    "Normalizer",
    "LowercaseNormalizer",
    "NoopNormalizer",
    "Tokenizer",
    "NoopTokenizer",
    "WhitespaceTokenizer",
]
