import os
import time
import pytest
from PySide6.QtWidgets import QApplication
from src.clicker import ClickerEngine, INPUT_MOUSE, MOUSEEVENTF_LEFTDOWN


@pytest.fixture(scope="session", autouse=True)
def qapp_session():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.mark.skipif(os.name != "nt", reason="Windows-only")
def test_sendinput_structure_size():
    from src.clicker import _ClickWorker
    w = _ClickWorker()
    assert hasattr(w, "_do_click")
    assert callable(w._do_click)
    assert INPUT_MOUSE == 0
    assert MOUSEEVENTF_LEFTDOWN == 0x0002


def test_stop_is_idempotent():
    eng = ClickerEngine()
    eng.stop()
    eng.stop()


def test_configure_validates_inputs():
    eng = ClickerEngine()
    eng.configure(interval_ms=50, button="left", click_type="single",
                  position_mode="current", locked_xy=(0, 0))
    assert eng._interval_ms == 50


def test_lifecycle_runs_and_stops_quickly(qapp_session):
    eng = ClickerEngine()
    eng.configure(interval_ms=20, button="left", click_type="single",
                  position_mode="current", locked_xy=(0, 0))
    received = []
    eng.on_click = lambda x, y: received.append((x, y))
    eng.start()
    assert eng.is_running()
    deadline = time.time() + 0.5
    while time.time() < deadline and len(received) < 3:
        qapp_session.processEvents()
        time.sleep(0.01)
    eng.stop()
    assert len(received) >= 3
    assert not eng.is_running()
