from __future__ import annotations

from autocomplete.normalizers.normalizer import Normalizer


class NoopNormalizer(Normalizer):
    def normalize(self, text: str) -> str:
        return text
