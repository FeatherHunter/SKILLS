import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from src.config import AppConfig
from src.clicker import ClickerEngine
from src.hotkeys import GlobalHotkeyManager
from src.main_window import MainWindow


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.mark.skipif(os.name != "nt", reason="Windows-only")
def test_window_creates_and_renders(qapp):
    config = AppConfig()
    clicker = ClickerEngine()
    hotkeys = GlobalHotkeyManager(on_activate=lambda _: None)
    win = MainWindow(config, clicker, hotkeys)
    win.show()
    qapp.processEvents()
    assert win.isVisible()
    assert win.width() >= 380
    assert win.height() >= 480
    QTimer.singleShot(50, win.close)
    qapp.processEvents()
