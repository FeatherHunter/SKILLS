"""Cursor indicator: a small always-on-top dot that follows the cursor.
Red when clicker is running, blue when stopped. Click-through so it never
interferes with autoclicker targets."""
from __future__ import annotations
import ctypes
import os
import sys
from ctypes import wintypes
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget


def _ilog(msg: str) -> None:
    """Append diagnostic line to %TEMP%/autoclicker_indicator.log."""
    try:
        log = Path(os.environ.get("TEMP", ".")) / "autoclicker_indicator.log"
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"{msg}\n")
    except OSError:
        pass


class ClickIndicator(QWidget):
    """Translucent always-on-top dot following the cursor."""

    DOT_DIAMETER = 14

    def __init__(self, parent=None):
        super().__init__(parent)
        # Qt.WindowTransparentForInput is the Qt-native way to make a window
        # click-through / mouse-event-transparent. It's applied at the Qt
        # level (no Win32 SetWindowLongW needed) and reliably prevents the
        # overlay from intercepting mouse events — without it the dot would
        # eat events under the cursor and feel like the mouse is "stuck".
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool  # hide from taskbar / alt-tab
            | Qt.WindowDoesNotAcceptFocus
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        # Belt-and-suspenders: also set Qt-level mouse-event-transparent
        # attribute. WS_EX_TRANSPARENT via SetWindowLongW is flaky on some
        # Qt versions — Qt attributes are reliable.
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setFixedSize(self.DOT_DIAMETER, self.DOT_DIAMETER)

        self._running = False
        self._follow_call_count = 0
        # Position timer — ~60Hz, cheap (single Win32 call + move())
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._follow_cursor)

        # Belt-and-suspenders: also set Win32 WS_EX_TRANSPARENT after the
        # window is shown. winId() before show() may return a placeholder
        # HWND; SetWindowLongW on it is lost when the real HWND is created.
        self._ws_ex_applied = False

    def showEvent(self, event):
        super().showEvent(event)
        if not self._ws_ex_applied and sys.platform == "win32":
            try:
                hwnd = int(self.winId())
                user32 = ctypes.windll.user32
                GWL_EXSTYLE = -20
                WS_EX_TRANSPARENT = 0x00000020
                WS_EX_LAYERED = 0x00080000
                WS_EX_TOOLWINDOW = 0x00000080
                style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                user32.SetWindowLongW(
                    hwnd, GWL_EXSTYLE,
                    style | WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW,
                )
                self._ws_ex_applied = True
            except (AttributeError, OSError):
                pass

    def set_running(self, running: bool):
        """Toggle color: True = red (running), False = blue (stopped)."""
        self._running = running
        _ilog(f"set_running({running})")
        self.update()

    def show(self):
        super().show()
        self._timer.start()
        _ilog(f"show() called hwnd={int(self.winId())} size={self.width()}x{self.height()} visible={self.isVisible()}")

    def hideEvent(self, event):
        self._timer.stop()
        _ilog("hideEvent — timer stopped")
        super().hideEvent(event)

    def _follow_cursor(self):
        self._follow_call_count += 1
        if sys.platform != "win32":
            return
        try:
            pt = wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        except OSError:
            return
        new_x = pt.x - self.width() // 2
        new_y = pt.y - self.height() // 2
        # Log first 5 calls + every 200th for sanity-check
        log_now = (self._follow_call_count <= 5
                   or self._follow_call_count % 200 == 0)
        if log_now:
            try:
                cur_pos = self.pos()
                _ilog(f"_follow #{self._follow_call_count} cursor=({pt.x},{pt.y}) "
                      f"want=({new_x},{new_y}) "
                      f"qt_pos=({cur_pos.x()},{cur_pos.y()}) "
                      f"screen_geo={self.screen().geometry().getRect() if self.screen() else None} "
                      f"device_pixel_ratio={self.devicePixelRatio()}")
            except OSError:
                pass
        # Move via Qt API (which goes through Win32 internally and keeps Qt's
        # internal pos() state in sync). SYSTEM_AWARE DPI means physical and
        # logical coords are the same — no scaling needed.
        self.move(new_x, new_y)
        # Also force absolute topmost via Win32 in case Qt's hint gets ignored.
        if log_now:
            try:
                hwnd = int(self.winId())
                ctypes.windll.user32.SetWindowPos(
                    hwnd, -1, 0, 0, 0, 0,
                    0x0001 | 0x0002 | 0x0010,  # NOSIZE | NOMOVE | NOACTIVATE
                )
            except (OSError, AttributeError):
                pass

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # Outer translucent ring for visibility against any background
        ring_color = QColor(255, 60, 60, 60) if self._running else QColor(60, 130, 255, 60)
        painter.setBrush(ring_color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(self.rect().adjusted(-2, -2, 2, 2))
        # Solid filled center
        core_color = QColor(220, 50, 50) if self._running else QColor(50, 110, 230)
        painter.setBrush(core_color)
        painter.drawEllipse(self.rect().adjusted(3, 3, -3, -3))