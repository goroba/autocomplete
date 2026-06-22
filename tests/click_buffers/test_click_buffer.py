import pytest

from autocomplete.click_buffers.click_buffer import ClickBuffer


def test_click_buffer_cannot_be_instantiated():
    with pytest.raises(TypeError):
        ClickBuffer()
