from autocomplete.normalizers.noop_normalizer import NoopNormalizer


def test_noop_normalizer_returns_text_unchanged():
    normalizer = NoopNormalizer()
    assert normalizer.normalize("Hello") == "Hello"


def test_noop_normalizer_empty_string():
    normalizer = NoopNormalizer()
    assert normalizer.normalize("") == ""


def test_noop_normalizer_mixed_case():
    normalizer = NoopNormalizer()
    assert normalizer.normalize("HeLLo WoRLd") == "HeLLo WoRLd"
