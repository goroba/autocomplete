from autocomplete.normalizers.lowercase_normalizer import LowercaseNormalizer


def test_lowercase_normalizer_lowers_text():
    normalizer = LowercaseNormalizer()
    assert normalizer.normalize("Hello") == "hello"


def test_lowercase_normalizer_empty_string():
    normalizer = LowercaseNormalizer()
    assert normalizer.normalize("") == ""


def test_lowercase_normalizer_mixed_case():
    normalizer = LowercaseNormalizer()
    assert normalizer.normalize("HeLLo WoRLd") == "hello world"
