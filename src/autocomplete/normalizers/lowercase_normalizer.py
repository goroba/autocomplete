from __future__ import annotations

from autocomplete.normalizers import Normalizer


class LowercaseNormalizer(Normalizer):
    def normalize(self, text: str) -> str:
        return text.lower()
