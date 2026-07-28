"""Verify global hotkey works regardless of which window has focus, even
when our own window is hidden (tray mode).

These tests REQUIRE a real Windows HWND. The 'offscreen' Qt platform
returns a fake HWND that rejects RegisterHotKey, so we skip when not on
a real Windows desktop."""
import os

import ctypes
from ctypes import wintypes
import time

import pytest
from PySide6.QtWidgets import QApplication

from src.clicker import ClickerEngine
from src.config import AppConfig
from src.hotkeys import GlobalHotkeyManager
from src.main_window import MainWindow
from src.styles import apply_app_style

# These tests use Win32 RegisterHotKey — only works with a real Windows HWND.
# offscreen Qt platform returns a bogus HWND where RegisterHotKey fails.
requires_real_windows_display = pytest.mark.skipif(
    os.environ.get("QT_QPA_PLATFORM") == "offscreen",
    reason="RegisterHotKey needs real Windows HWND, not offscreen platform",
)


@pytest.fixture(scope="session", autouse=True)
def qapp_session():
    if "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    yield QApplication.instance() or QApplication([])


def _send_wm_hotkey(hwnd: int, hotkey_id: int):
    """Simulate Windows delivering WM_HOTKEY to our window's message queue,
    as if the user pressed the hotkey while another app had focus."""
    WM_HOTKEY = 0x0312
    user32 = ctypes.windll.user32
    user32.PostMessageW(hwnd, WM_HOTKEY, hotkey_id, 0)


@requires_real_windows_display
def _setup(qapp_session, hotkey_toggle="`"):
    """Standard setup: window shown, all 3 hotkeys registered."""
    config = AppConfig(hotkey_toggle=hotkey_toggle)
    clicker = ClickerEngine()
    hotkeys = GlobalHotkeyManager(on_activate=lambda _: None)
    win = MainWindow(config, clicker, hotkeys)
    win.show()
    qapp_session.processEvents()
    # Mimic what app.py does after MainWindow creation
    ok = hotkeys.register_all(
        toggle=hotkey_toggle, panic="Esc", show="Ctrl+Shift+A"
    )
    if not ok:
        print(f"\nDEBUG: hotkey registration failed.")
        print(f"  failed: {hotkeys.failed_hotkeys()}")
        print(f"  specs: {hotkeys._specs}")
        print(f"  hwnd: {win._hwnd}")
    assert ok, "hotkey registration failed"
    return win, hotkeys


def _find_id(hotkeys, name):
    """Find the hotkey ID that was actually passed to RegisterHotKey.
    On non-Windows test path the ID is len+1; on Windows it's len+1 too
    after register_all pre-populates 1,2,3."""
    candidates = [hid for hid, n in hotkeys._handles.items() if n == name]
    # RegisterHotKey was called with the LAST id assigned for this name
    # (because _register appends to _handles).
    return candidates[-1]


@requires_real_windows_display
def test_hotkey_filter_installed(qapp_session):
    """Verify that attach() actually installs the QApplication native event
    filter — this is what makes the hotkey work in real Windows."""
    win, hotkeys = _setup(qapp_session)
    assert hotkeys._filter is not None, \
        "attach() did not install the native event filter"
    hwnd = win._hwnd
    assert hwnd > 0

    events = []
    hotkeys._on_activate = lambda name: events.append(name)
    toggle_id = _find_id(hotkeys, "toggle")
    _send_wm_hotkey(hwnd, toggle_id)

    for _ in range(10):
        qapp_session.processEvents()
        time.sleep(0.01)
    assert "toggle" in events, f"hotkey not delivered (events={events})"


@requires_real_windows_display
def test_hotkey_works_with_window_hidden(qapp_session):
    """Closing window with X hides it to tray. Hotkey must still work."""
    win, hotkeys = _setup(qapp_session)
    hwnd = win._hwnd
    win.hide()
    qapp_session.processEvents()
    assert not win.isVisible()

    events = []
    hotkeys._on_activate = lambda name: events.append(name)
    toggle_id = _find_id(hotkeys, "toggle")
    _send_wm_hotkey(hwnd, toggle_id)
    for _ in range(10):
        qapp_session.processEvents()
        time.sleep(0.01)
    assert "toggle" in events, "hotkey broken after window hide"


@requires_real_windows_display
def test_hotkey_works_for_all_three(qapp_session):
    win, hotkeys = _setup(qapp_session)
    hwnd = win._hwnd
    events = []
    hotkeys._on_activate = lambda name: events.append(name)

    for name in ("toggle", "panic", "show"):
        hid = _find_id(hotkeys, name)
        _send_wm_hotkey(hwnd, hid)
        for _ in range(5):
            qapp_session.processEvents()
            time.sleep(0.01)

    assert "toggle" in events
    assert "panic" in events
    assert "show" in events


@requires_real_windows_display
def test_hotkey_works_after_window_close_to_tray(qapp_session):
    """The full close-button-to-tray scenario: window closes, app stays
    alive, hotkey must still work (user explicitly closed window but didn't
    quit the app). This is THE key behavior the user asked about."""
    win, hotkeys = _setup(qapp_session)
    hwnd = win._hwnd

    # Simulate closeEvent handler (X button)
    win.closeEvent_result = None
    win.close()
    # closeEvent calls event.ignore() and self.hide() — window hidden but alive
    qapp_session.processEvents()
    assert not win.isVisible()

    # Hotkey should still work
    events = []
    hotkeys._on_activate = lambda name: events.append(name)
    toggle_id = _find_id(hotkeys, "toggle")
    _send_wm_hotkey(hwnd, toggle_id)
    for _ in range(10):
        qapp_session.processEvents()
        time.sleep(0.01)
    assert "toggle" in events, "hotkey broken after window close (tray mode)"