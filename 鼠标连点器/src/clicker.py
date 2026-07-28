"""ClickerEngine: runs an isolated click loop on a QThread.
Uses ctypes SendInput for low-level input injection on Windows."""
from __future__ import annotations
import ctypes
import sys
import threading
import time
from ctypes import wintypes
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QApplication


MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040

INPUT_MOUSE = 0


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("u", INPUT_UNION),
    ]


_BUTTON_DOWN = {
    "left": MOUSEEVENTF_LEFTDOWN,
    "right": MOUSEEVENTF_RIGHTDOWN,
    "middle": MOUSEEVENTF_MIDDLEDOWN,
}
_BUTTON_UP = {
    "left": MOUSEEVENTF_LEFTUP,
    "right": MOUSEEVENTF_RIGHTUP,
    "middle": MOUSEEVENTF_MIDDLEUP,
}


def _clamp_to_screen(x: int, y: int) -> tuple[int, int]:
    """Clamp absolute screen coordinates to the virtual screen bounds.
    SetCursorPos fails silently for off-screen coords."""
    if sys.platform != "win32":
        return x, y
    user32 = ctypes.windll.user32
    SM_CXVIRTUALSCREEN = 78
    SM_CYVIRTUALSCREEN = 79
    SM_XVIRTUALSCREEN = 76
    SM_YVIRTUALSCREEN = 77
    w = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    h = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    ox = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    oy = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    return (
        max(ox, min(x, ox + w - 1)),
        max(oy, min(y, oy + h - 1)),
    )


def _send_click_native(x: int, y: int, button: str, click_type: str) -> None:
    if sys.platform != "win32":
        return
    down_flag = _BUTTON_DOWN[button]
    up_flag = _BUTTON_UP[button]
    n_clicks = 2 if click_type == "double" else 1

    user32 = ctypes.windll.user32
    x, y = _clamp_to_screen(x, y)
    user32.SetCursorPos(x, y)
    zero = ctypes.pointer(ctypes.c_ulong(0))
    for _ in range(n_clicks):
        for down in (True, False):
            inp = INPUT()
            inp.type = INPUT_MOUSE
            inp.u.mi.dx = 0
            inp.u.mi.dy = 0
            inp.u.mi.mouseData = 0
            inp.u.mi.dwFlags = down_flag if down else up_flag
            inp.u.mi.time = 0
            inp.u.mi.dwExtraInfo = zero
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        if n_clicks == 2:
            ctypes.windll.kernel32.Sleep(15)


def _get_cursor_pos() -> tuple[int, int]:
    pt = wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


class _ClickWorker(QObject):
    """Per-run worker that lives in the worker thread. Destroyed when stop()."""
    started = Signal()
    stopped = Signal()
    stats_updated = Signal(int, int)
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._interval_ms = 100
        self._button = "left"
        self._click_type = "single"
        self._position_mode = "follow"
        self._locked_xy_at_start: tuple[int, int] | None = None
        self._running = False
        self._count = 0
        self._start_ts_ms = 0
        self.on_click = None

    def configure(self, *, interval_ms, button, click_type, position_mode,
                  locked_xy, locked_xy_at_start):
        self._interval_ms = interval_ms
        self._button = button
        self._click_type = click_type
        self._position_mode = position_mode
        self._locked_xy_at_start = locked_xy_at_start

    def _resolve_xy(self) -> tuple[int, int]:
        if self._position_mode == "current":
            if self._locked_xy_at_start is None:
                self._locked_xy_at_start = _get_cursor_pos()
            return self._locked_xy_at_start
        return _get_cursor_pos()  # follow

    def _do_click(self, x: int, y: int):
        try:
            _send_click_native(x, y, self._button, self._click_type)
        except Exception as e:  # noqa: BLE001 - keep loop alive
            self.error.emit(str(e))

    def _loop(self) -> None:
        # Initialize run state in the worker thread
        self._running = True
        self._count = 0
        self._start_ts_ms = int(time.time() * 1000)
        self.started.emit()
        try:
            last_stats_emit_ms = 0
            STATS_THROTTLE_MS = 100  # emit stats at most ~10Hz regardless of click rate
            while self._running:
                x, y = self._resolve_xy()
                if self.on_click is not None:
                    self.on_click(x, y)
                else:
                    self._do_click(x, y)
                self._count += 1
                elapsed = int(time.time() * 1000) - self._start_ts_ms
                # Throttle stats emit so 100Hz click loops don't flood UI queue.
                # Always emit on first tick and on last tick (when loop exits).
                if elapsed - last_stats_emit_ms >= STATS_THROTTLE_MS:
                    self.stats_updated.emit(self._count, elapsed)
                    last_stats_emit_ms = elapsed
                slept = 0
                slice_ms = 10
                while slept < self._interval_ms and self._running:
                    QThread.msleep(slice_ms)
                    slept += slice_ms
        finally:
            # Final stats emit so user sees the exact final count, not the
            # throttled value from up to 100ms ago.
            elapsed = int(time.time() * 1000) - self._start_ts_ms
            self.stats_updated.emit(self._count, elapsed)
            self._running = False
            self.stopped.emit()


class ClickerEngine(QObject):
    """Owns the click loop. Stays on main thread; spawns a _ClickWorker on a
    fresh QThread each start(). Re-using the same QThread across multiple
    runs does not work reliably in Qt (moveToThread from a destroyed thread
    is a no-op)."""

    started = Signal()
    stopped = Signal()
    stats_updated = Signal(int, int)
    error = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._interval_ms = 100
        self._button = "left"
        self._click_type = "single"
        self._position_mode = "follow"
        self._locked_xy_at_start: tuple[int, int] | None = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: QThread | None = None
        self._worker: _ClickWorker | None = None
        self.on_click = None

    def configure(self, *, interval_ms: int, button: str, click_type: str,
                  position_mode: str, locked_xy: tuple[int, int]) -> None:
        self._interval_ms = max(10, min(int(interval_ms), 10000))
        self._button = button if button in ("left", "right", "middle") else "left"
        self._click_type = click_type if click_type in ("single", "double") else "single"
        self._position_mode = position_mode if position_mode in ("current", "follow") else "follow"
        if position_mode == "current":
            self._locked_xy_at_start = None
        else:
            self._locked_xy_at_start = locked_xy

    def reset_captured_position(self) -> None:
        with self._lock:
            self._locked_xy_at_start = None

    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._worker = _ClickWorker()
            self._worker.configure(
                interval_ms=self._interval_ms,
                button=self._button,
                click_type=self._click_type,
                position_mode=self._position_mode,
                locked_xy=(0, 0),
                locked_xy_at_start=self._locked_xy_at_start,
            )
            self._worker.on_click = self.on_click
            self._thread = QThread()
            self._worker.moveToThread(self._thread)
            # Bridge: worker signals → engine signals (cross-thread queued)
            self._worker.started.connect(self.started)
            self._worker.stopped.connect(self.stopped)
            self._worker.stats_updated.connect(self.stats_updated)
            self._worker.error.connect(self.error)
            self._thread.started.connect(self._worker._loop)
            self._thread.finished.connect(self._worker.deleteLater)
            self._thread.finished.connect(self._thread.deleteLater)
            self._running = True
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            if not self._running and self._thread is None:
                return
            worker = self._worker
            thread = self._thread
            self._worker = None
            self._thread = None
            self._running = False
        # Tell worker to stop. _running is a plain bool — cross-thread writes
        # are atomic in CPython and read by _loop's busy-wait slice check.
        # Direct write (NOT invokeMethod/Queued) is required because the
        # worker thread is busy in _loop with no event loop running, so
        # queued calls would never be delivered.
        if worker is not None:
            worker._running = False
        if thread is not None:
            thread.quit()
            if not thread.wait(2000):
                # Thread didn't respond in 2s. Best-effort safety: ensure
                # mouse button is released in case we're mid-click, THEN
                # terminate. Without this, mouse can stay "down" stuck state.
                self._release_button_safely()
                thread.terminate()
                thread.wait(1000)
            # thread.deleteLater is connected to finished signal

    @staticmethod
    def _release_button_safely() -> None:
        """Send a release event for any button we might have pressed.
        Best-effort — no-op if no press is in flight."""
        if sys.platform != "win32":
            return
        # Send UP for all 3 buttons to cover any mid-click state.
        # We can't tell which button was down; sending all is safe (idempotent).
        for up_flag in (MOUSEEVENTF_LEFTUP, MOUSEEVENTF_RIGHTUP, MOUSEEVENTF_MIDDLEUP):
            inp = INPUT()
            inp.type = INPUT_MOUSE
            inp.u.mi.dx = 0
            inp.u.mi.dy = 0
            inp.u.mi.mouseData = 0
            inp.u.mi.dwFlags = up_flag
            inp.u.mi.time = 0
            inp.u.mi.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))
            try:
                ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
            except OSError:
                pass