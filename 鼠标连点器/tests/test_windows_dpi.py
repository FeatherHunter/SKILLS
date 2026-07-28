import os
import pytest
from src.windows_dpi import enable_dpi_awareness, clamp_to_screen

@pytest.mark.skipif(os.name != "nt", reason="Windows-only")
def test_enable_dpi_awareness_runs_without_error():
    enable_dpi_awareness()
    enable_dpi_awareness()


@pytest.mark.parametrize("x,y,w,h,expected", [
    (10, 10, 1920, 1080, (10, 10)),
    (-5, 10, 1920, 1080, (0, 10)),
    (2500, 10, 1920, 1080, (1919, 10)),
    (10, -5, 1920, 1080, (10, 0)),
    (10, 1500, 1920, 1080, (10, 1079)),
])
def test_clamp_to_screen(x, y, w, h, expected):
    assert clamp_to_screen(x, y, w, h) == expected
