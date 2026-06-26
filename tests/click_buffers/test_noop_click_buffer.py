from autocomplete.click_buffers import NoopClickBuffer


def test_click_to_score_returns_zero():
    buffer = NoopClickBuffer()

    assert buffer.click_to_score(1) == 0.0
    assert buffer.click_to_score(3) == 0.0


def test_click_does_nothing():
    buffer = NoopClickBuffer()

    buffer.click("Red Apple", clicks=3)


def test_flush_returns_empty():
    buffer = NoopClickBuffer()

    assert list(buffer.flush()) == []


def test_iter_returns_empty():
    buffer = NoopClickBuffer()

    assert list(buffer) == []
