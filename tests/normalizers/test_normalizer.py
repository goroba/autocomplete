import pytest

from autocomplete.normalizers import Normalizer


def test_normalizer_cannot_be_instantiated():
    with pytest.raises(TypeError):
        Normalizer()
