from unittest.mock import Mock

from autocomplete.click_buffers.noop_click_buffer import NoopClickBuffer


def test_noop_click_buffer_default_click_rate():
    buffer = NoopClickBuffer()

    assert buffer.click_rate == 1.0


def test_click_to_score_scales_clicks_by_click_rate():
    buffer = NoopClickBuffer(click_rate=0.5)

    assert buffer.click_to_score(1) == 0.5
    assert buffer.click_to_score(3) == 1.5


def test_click_rescores_with_click_rate():
    client = Mock()
    buffer = NoopClickBuffer(click_rate=0.5)
    buffer.set_client(client)

    buffer.click("Red Apple")

    client.rescore.assert_called_once_with("Red Apple", 0.5)


def test_click_rescores_with_amount():
    client = Mock()
    buffer = NoopClickBuffer(click_rate=0.5)
    buffer.set_client(client)

    buffer.click("Red Apple", clicks=3)

    client.rescore.assert_called_once_with("Red Apple", 1.5)


def test_flush_returns_empty():
    buffer = NoopClickBuffer()

    assert list(buffer.flush()) == []
