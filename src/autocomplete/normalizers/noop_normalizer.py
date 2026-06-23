from __future__ import annotations

from autocomplete.normalizers import Normalizer


class NoopNormalizer(Normalizer):
    def normalize(self, text: str) -> str:
        return text
