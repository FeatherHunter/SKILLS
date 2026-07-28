"""Verify that rapid stop-then-start (or start-then-stop) does NOT leave two
_concurrent _loop threads running. This is B17 regression."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import time

import pytest
from PySide6.QtWidgets import QApplication

from src.clicker import ClickerEngine


@pytest.fixture(scope="session", autouse=True)
def qapp_session():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    yield app


def test_rapid_stop_start_does_not_create_two_loops(qapp_session):
    """Bug B17: stop() released lock before wait() → start() could create a 2nd
    QThread + _loop concurrently. After fix, stop() holds lock through wait,
    so start() must wait for stop() to fully tear down."""
    eng = ClickerEngine()
    eng.configure(interval_ms=20, button="left", click_type="single",
                  position_mode="current", locked_xy=(0, 0))
    received = []
    eng.on_click = lambda x, y: received.append((x, y))

    eng.start()
    assert eng.is_running()
    deadline = time.time() + 0.12
    while time.time() < deadline:
        qapp_session.processEvents()
        time.sleep(0.005)
    count_before = len(received)
    assert count_before > 0

    eng.stop()
    assert not eng.is_running()

    # CRITICAL: immediately start again. With the bug, two QThreads would run.
    eng.start()
    assert eng.is_running()

    deadline = time.time() + 0.12
    while time.time() < deadline:
        qapp_session.processEvents()
        time.sleep(0.005)
    count_after = len(received)
    # After the second start, we should get MORE clicks. If two loops were
    # running concurrently, we'd see roughly 2x the expected count.
    assert count_after > count_before, \
        f"second start produced no clicks (before={count_before}, after={count_after})"

    eng.stop()
    assert not eng.is_running()