from __future__ import annotations

from autocomplete.tokenizers import Tokenizer


class NoopTokenizer(Tokenizer):
    def tokenize(self, text: str) -> list[str]:
        return [text]
