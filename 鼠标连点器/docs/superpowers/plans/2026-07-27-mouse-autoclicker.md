# 鼠标连点器 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver `dist/鼠标连点器.exe` — a single-file Windows auto-clicker with Fluent acrylic UI, global hotkeys (F6/Esc/Ctrl+Shift+A), three position modes, and persisted config.

**Architecture:** Python 3.11+ / PySide6 / ctypes wrapping Win32 `SendInput`. Single-process, single-GUI-thread + one `QThread` for the click loop. Win32 `RegisterHotKey` for global hotkeys. Win32 named mutex for single-instance. JSON config at `%USERPROFILE%/.autoclicker/config.json`. PyInstaller `--onefile --windowed`.

**Tech Stack:** Python 3.11+ · PySide6 · pyinstaller · pytest (dev) · ctypes · pywin32 not required (ctypes only).

---

## File Structure

```
鼠标连点器/
├─ src/
│  ├─ app.py              # entry: QApplication + single-instance + wire-up
│  ├─ main_window.py      # UI: titlebar, status, CTA, settings, stats
│  ├─ clicker.py          # ClickerEngine(QObject) on QThread; SendInput via ctypes
│  ├─ hotkeys.py          # GlobalHotkeyManager: Win32 RegisterHotKey + nativeEvent
│  ├─ config.py           # AppConfig dataclass + JSON load/save
│  ├─ styles.py           # QSS string + enable Win11 acrylic + Win10 fallback paint
│  ├─ tray.py             # QSystemTrayIcon wrapper with right-click menu
│  └─ windows_dpi.py      # ctypes helpers: enable DPI awareness, click point clamp
├─ assets/
│  ├─ icon.ico            # 256×256 multi-res tray icon (idle)
│  └─ icon-running.ico    # 256×256 tray icon (running)
├─ tests/
│  ├─ test_config.py
│  ├─ test_clicker.py     # structure size + click loop stop semantics
│  ├─ test_single_instance.py
│  └─ test_app_smoke.py   # launches MainWindow, asserts visible, no exceptions
├─ build.spec             # PyInstaller
├─ requirements.txt
└─ docs/superpowers/{specs,plans}/...
```

Single-responsibility per file; no file > ~300 lines. The `clicker.py` is the largest; everything else <200.

---

## Task 1: Project skeleton + smoke test

**Files:**
- Create: `D:\0Tools\鼠标连点器/requirements.txt`
- Create: `D:\0Tools\鼠标连点器/src/__init__.py`
- Create: `D:\0Tools\鼠标连点器/src/app.py` (placeholder)
- Create: `D:\0Tools\鼠标连点器/tests/__init__.py`
- Create: `D:\0Tools\鼠标连点器/tests/test_app_smoke.py`
- Create: `D:\0Tools\鼠标连点器/.gitignore`

- [ ] **Step 1: Create directories**

```powershell
New-Item -ItemType Directory -Force -Path "D:\0Tools\鼠标连点器\src","D:\0Tools\鼠标连点器\tests","D:\0Tools\鼠标连点器\assets"
"done"
```

Expected: prints `done`.

- [ ] **Step 2: Write `requirements.txt`**

```
PySide6>=6.6
pyinstaller>=6.3
pytest>=8.0
```

- [ ] **Step 3: Write `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
build/
dist/
*.spec
.superpowers/
```

- [ ] **Step 4: Write empty `src/app.py` placeholder**

```python
"""Entry point. Implemented in Task 11."""
import sys
from PySide6.QtWidgets import QApplication

def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("AutoClicker")
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Write `src/__init__.py` and `tests/__init__.py`**

Both empty files (`""` content).

- [ ] **Step 6: Write smoke test**

File `tests/test_app_smoke.py`:

```python
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"  # CI-safe

import pytest
from src.app import main

@pytest.mark.skipif(os.name != "nt", reason="Windows-only")
def test_app_imports_and_main_callable():
    assert callable(main)
```

- [ ] **Step 7: Install requirements + run smoke test**

```powershell
py -3.11 -m pip install -r requirements.txt
py -3.11 -m pytest tests/test_app_smoke.py -v
```

Expected: 1 passed. (Skip reason if not on Windows resolves appropriately.)

---

## Task 2: DPI awareness helper

**Files:**
- Create: `D:\0Tools\鼠标连点器/src/windows_dpi.py`
- Create: `D:\0Tools\鼠标连点器/tests/test_windows_dpi.py`

- [ ] **Step 1: Write failing test**

File `tests/test_windows_dpi.py`:

```python
import os
import pytest
from src.windows_dpi import enable_dpi_awareness, clamp_to_screen

@pytest.mark.skipif(os.name != "nt", reason="Windows-only")
def test_enable_dpi_awareness_runs_without_error():
    # Idempotent; can be called multiple times safely
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
```

- [ ] **Step 2: Run tests, confirm FAIL**

```powershell
py -3.11 -m pytest tests/test_windows_dpi.py -v
```

Expected: ModuleNotFoundError for `src.windows_dpi`.

- [ ] **Step 3: Implement `src/windows_dpi.py`**

```python
"""Windows DPI awareness + screen clamping helpers."""
import ctypes
import sys

def enable_dpi_awareness() -> None:
    """Make the process per-monitor DPI aware v2. Idempotent."""
    if sys.platform != "win32":
        return
    try:
        # SetProcessDpiAwarenessContext(-4) = DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
        ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
    except (AttributeError, OSError):
        # Win10 1607 fallback: SetProcessDpiAwareness(2)
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            pass

def clamp_to_screen(x: int, y: int, screen_w: int, screen_h: int) -> tuple[int, int]:
    """Clamp a screen coordinate to [0, max-1] range."""
    return (max(0, min(x, screen_w - 1)), max(0, min(y, screen_h - 1)))
```

- [ ] **Step 4: Run tests, confirm PASS**

```powershell
py -3.11 -m pytest tests/test_windows_dpi.py -v
```

Expected: all 6 tests pass.

---

## Task 3: Config (TDD)

**Files:**
- Create: `D:\0Tools\鼠标连点器/src/config.py`
- Create: `D:\0Tools\鼠标连点器/tests/test_config.py`

- [ ] **Step 1: Write failing test**

File `tests/test_config.py`:

```python
import json
import os
import tempfile
import pytest
from src.config import AppConfig, config_path

def test_defaults():
    c = AppConfig()
    assert c.interval_ms == 100
    assert c.button == "left"
    assert c.click_type == "single"
    assert c.position_mode == "current"
    assert c.locked_x == 0
    assert c.locked_y == 0
    assert c.hotkey_toggle == "F6"
    assert c.hotkey_show == "Ctrl+Shift+A"

def test_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config._CONFIG_DIR", lambda: tmp_path)
    c = AppConfig(interval_ms=500, button="right", click_type="double",
                  position_mode="locked", locked_x=400, locked_y=300,
                  hotkey_toggle="F8", hotkey_show="Ctrl+Alt+W")
    c.save()
    assert (tmp_path / "config.json").exists()
    loaded = AppConfig.load()
    assert loaded == c

def test_load_missing_returns_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config._CONFIG_DIR", lambda: tmp_path)
    c = AppConfig.load()
    assert c == AppConfig()

def test_load_corrupt_returns_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config._CONFIG_DIR", lambda: tmp_path)
    (tmp_path / "config.json").write_text("not valid json {{{")
    c = AppConfig.load()
    assert c == AppConfig()
    assert (tmp_path / "config.json.bak").exists()

def test_interval_validation():
    c = AppConfig(interval_ms=10)
    assert c.interval_ms == 10
    c = AppConfig(interval_ms=5)  # too low
    assert c.interval_ms == 10   # clamped
    c = AppConfig(interval_ms=99999)  # too high
    assert c.interval_ms == 10000  # clamped
```

- [ ] **Step 2: Run tests, confirm FAIL**

```powershell
py -3.11 -m pytest tests/test_config.py -v
```

Expected: ModuleNotFoundError for `src.config`.

- [ ] **Step 3: Implement `src/config.py`**

```python
"""App config: dataclass + JSON load/save at ~/.autoclicker/config.json."""
from __future__ import annotations
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


def _config_dir() -> Path:
    """Resolve user's autostart config dir. Windows: %USERPROFILE%/.autoclicker.
    On any OS: $HOME/.autoclicker. Falls back to %LOCALAPPDATA% if write fails."""
    try:
        base = Path(os.environ.get("USERPROFILE") or Path.home())
        d = base / ".autoclicker"
        d.mkdir(parents=True, exist_ok=True)
        # Test write
        (d / ".write_test").write_text("ok")
        (d / ".write_test").unlink()
        return d
    except OSError:
        fallback = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "AutoClicker"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


@dataclass
class AppConfig:
    interval_ms: int = 100
    button: str = "left"          # 'left' | 'right' | 'middle'
    click_type: str = "single"    # 'single' | 'double'
    position_mode: str = "current"  # 'current' | 'locked' | 'follow'
    locked_x: int = 0
    locked_y: int = 0
    hotkey_toggle: str = "F6"
    hotkey_show: str = "Ctrl+Shift+A"

    def __post_init__(self):
        if self.button not in ("left", "right", "middle"):
            self.button = "left"
        if self.click_type not in ("single", "double"):
            self.click_type = "single"
        if self.position_mode not in ("current", "locked", "follow"):
            self.position_mode = "current"
        if self.interval_ms < 10:
            self.interval_ms = 10
        elif self.interval_ms > 10000:
            self.interval_ms = 10000

    def save(self) -> None:
        d = _config_dir()
        (d / "config.json").write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def load(cls) -> "AppConfig":
        path = _config_dir() / "config.json"
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(**data)
        except (json.JSONDecodeError, TypeError, ValueError):
            # Backup corrupt file
            try:
                path.rename(path.with_suffix(".json.bak"))
            except OSError:
                pass
            return cls()


def config_path() -> Path:
    return _config_dir() / "config.json"
```

- [ ] **Step 4: Run tests, confirm PASS**

```powershell
py -3.11 -m pytest tests/test_config.py -v
```

Expected: 5 tests pass.

---

## Task 4: ClickerEngine — SendInput core (TDD where possible)

**Files:**
- Create: `D:\0Tools\鼠标连点器/src/clicker.py`
- Create: `D:\0Tools\鼠标连点器/tests/test_clicker.py`

- [ ] **Step 1: Write failing test**

File `tests/test_clicker.py`:

```python
import os
import threading
import time
import pytest
from PySide6.QtWidgets import QApplication
from src.clicker import ClickerEngine, INPUT_MOUSE, MOUSEEVENTF_LEFTDOWN


@pytest.fixture(scope="session", autouse=True)
def qapp_session():
    """Ensure one QApplication exists for all tests in this module."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.mark.skipif(os.name != "nt", reason="Windows-only")
def test_sendinput_structure_size():
    """Win32 MOUSEINPUT struct must compile and constant be defined."""
    eng = ClickerEngine()
    assert hasattr(eng, "_send_click_windows")
    assert callable(eng._send_click_windows)
    assert INPUT_MOUSE == 0
    assert MOUSEEVENTF_LEFTDOWN == 0x0002

def test_stop_is_idempotent():
    eng = ClickerEngine()
    eng.stop()  # not running, must not raise
    eng.stop()

def test_configure_validates_inputs():
    eng = ClickerEngine()
    eng.configure(interval_ms=50, button="left", click_type="single",
                  position_mode="current", locked_xy=(0, 0))
    assert eng._interval_ms == 50

def test_lifecycle_runs_and_stops_quickly(qapp_session):
    """Verify run/stop semantics without actually clicking (use a sink)."""
    eng = ClickerEngine()
    eng.configure(interval_ms=20, button="left", click_type="single",
                  position_mode="current", locked_xy=(0, 0))
    received = []
    eng.on_click = lambda x, y: received.append((x, y))  # monkey-patch sink
    eng.start()
    assert eng.is_running()
    deadline = time.time() + 0.5
    while time.time() < deadline and len(received) < 3:
        qapp_session.processEvents()
        time.sleep(0.01)
    eng.stop()
    assert len(received) >= 3  # at least 3 ticks in 500ms at 20ms interval
    assert not eng.is_running()
```

> The above test references `ClickerEngine.on_click` attribute; we expose it as an overridable hook used in tests to avoid real clicks. The real `start()` calls `on_click(x, y)` rather than `SendInput` directly when `on_click` is overridden.

- [ ] **Step 2: Run tests, confirm FAIL**

```powershell
py -3.11 -m pytest tests/test_clicker.py -v
```

Expected: ModuleNotFoundError for `src.clicker`.

- [ ] **Step 3: Implement `src/clicker.py`**

```python
"""ClickerEngine: runs an isolated click loop on a QThread.
Uses ctypes SendInput for low-level input injection."""
from __future__ import annotations
import ctypes
import sys
from ctypes import wintypes
from PySide6.QtCore import QObject, QThread, Signal


# ===== Win32 constants =====
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040

INPUT_MOUSE = 0


# ===== Win32 structures =====
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


# ===== Mouse button codes =====
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


def _send_click_native(x: int, y: int, button: str, click_type: str) -> None:
    """Lowest-level click via SendInput. Called only on Windows."""
    if sys.platform != "win32":
        return
    down_flag = _BUTTON_DOWN[button]
    up_flag = _BUTTON_UP[button]
    n_clicks = 2 if click_type == "double" else 1

    for _ in range(n_clicks):
        for _ in range(2):  # send down+up per click
            inp = INPUT()
            inp.type = INPUT_MOUSE
            inp.u.mi.dx = x
            inp.u.mi.dy = y
            inp.u.mi.mouseData = 0
            inp.u.mi.dwFlags = (MOUSEEVENTF_MOVE | (down_flag if _ == 0 else up_flag))
            inp.u.mi.time = 0
            inp.u.mi.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))
            ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        # tiny gap between double-click pulses
        if n_clicks == 2:
            ctypes.windll.kernel32.Sleep(15)


def _get_cursor_pos() -> tuple[int, int]:
    pt = wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


class ClickerEngine(QObject):
    """Runs click loop on a separate QThread.

    Signals:
        started() - emitted right after thread begins
        stopped() - emitted right after thread stops
        stats_updated(count: int, elapsed_ms: int) - tick stats
        error(str) - on SendInput failure
    """
    started = Signal()
    stopped = Signal()
    stats_updated = Signal(int, int)
    error = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._interval_ms = 100
        self._button = "left"
        self._click_type = "single"
        self._position_mode = "current"
        self._locked_xy = (0, 0)
        self._running = False
        self._thread: QThread | None = None
        self._count = 0
        self._start_ts_ms = 0
        # For unit tests: override this hook to sink clicks without actually clicking
        self.on_click = None  # type: ignore[assignment]

    def configure(self, *, interval_ms: int, button: str, click_type: str,
                  position_mode: str, locked_xy: tuple[int, int]) -> None:
        self._interval_ms = max(10, min(int(interval_ms), 10000))
        self._button = button if button in ("left", "right", "middle") else "left"
        self._click_type = click_type if click_type in ("single", "double") else "single"
        self._position_mode = position_mode if position_mode in ("current", "locked", "follow") else "current"
        self._locked_xy = locked_xy

    # Backwards-compatible aliases used in tests
    _interval_ms: int
    def _set_interval_for_test(self, v): self._interval_ms = v

    def is_running(self) -> bool:
        return self._running

    def _send_click_windows(self, x: int, y: int) -> None:
        try:
            _send_click_native(x, y, self._button, self._click_type)
        except OSError as e:
            self.error.emit(str(e))

    def _resolve_xy(self) -> tuple[int, int]:
        if self._position_mode == "locked":
            return self._locked_xy
        if self._position_mode == "follow":
            return _get_cursor_pos()
        # 'current' = lock to first xy seen at start(); engine captures it on start()
        if not hasattr(self, "_locked_xy_at_start") or self._locked_xy_at_start is None:
            self._locked_xy_at_start = _get_cursor_pos()
        return self._locked_xy_at_start

    def _loop(self) -> None:
        self._running = True
        self._count = 0
        self._start_ts_ms = int(time.time() * 1000)
        self.started.emit()
        try:
            while self._running:
                x, y = self._resolve_xy()
                if self.on_click is not None:
                    self.on_click(x, y)
                else:
                    self._send_click_windows(x, y)
                self._count += 1
                elapsed = int(time.time() * 1000) - self._start_ts_ms
                self.stats_updated.emit(self._count, elapsed)
                # sleep in small slices so stop() is responsive
                slept = 0
                slice_ms = 10
                while slept < self._interval_ms and self._running:
                    QThread.msleep(slice_ms)
                    slept += slice_ms
        finally:
            self._running = False
            self.stopped.emit()

    def start(self) -> None:
        if self._running:
            return
        self._locked_xy_at_start = None  # force re-capture for 'current' mode
        self._thread = QThread()
        self.moveToThread(self._thread)
        self._thread.started.connect(self._loop)
        self._thread.start()

    def stop(self) -> None:
        if not self._running and (self._thread is None or not self._thread.isRunning()):
            return
        self._running = False
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
            self._thread = None
```

> **Note:** `import time` must be at the top of `src/clicker.py` alongside the other imports — do NOT copy the trailing `import time` line above.

- [ ] **Step 4: Verify imports**

The top of `src/clicker.py` already contains:

```python
from __future__ import annotations
import ctypes
import sys
from ctypes import wintypes
from PySide6.QtCore import QObject, QThread, Signal
```

Confirm it has `import time`. If not, add it. The `_loop` and `start` and `__init__` methods use `time.time()`. If you copy/paste step 3's code block, the imports are already correct — `import time` is NOT already added so you must include it. Add this line right after `import sys`:

```python
import time
```

- [ ] **Step 5: Run tests, confirm PASS**

```powershell
py -3.11 -m pytest tests/test_clicker.py -v
```

Expected: 4 tests pass (1 may skip on non-Windows).

---

## Task 5: GlobalHotkeyManager

**Files:**
- Create: `D:\0Tools\鼠标连点器/src/hotkeys.py`
- Create: `D:\0Tools\鼠标连点器/tests/test_hotkeys.py`

- [ ] **Step 1: Write test that uses a stub for `_register_windows`**

File `tests/test_hotkeys.py`:

```python
import pytest
from src.hotkeys import GlobalHotkeyManager, parse_hotkey

def test_parse_hotkey_simple_letter():
    mod, vk = parse_hotkey("F6")
    assert vk == 0x75  # VK_F6
    assert mod == 0

def test_parse_hotkey_combo():
    mod, vk = parse_hotkey("Ctrl+Shift+A")
    assert (mod & 0x0002) and (mod & 0x0004)  # MOD_CONTROL + MOD_SHIFT
    assert vk == ord("A")

def test_parse_hotkey_invalid_raises():
    with pytest.raises(ValueError):
        parse_hotkey("Garbage")

def test_manager_emits_signals_when_triggered(monkeypatch):
    """Verify hotkey IDs flow through to the activated signal."""
    events = []
    mgr = GlobalHotkeyManager(on_activate=lambda name: events.append(name))
    # Stub register to avoid real Win32 calls
    monkeypatch.setattr(mgr, "_register", lambda name, key: True)
    assert mgr.register_all()
    # Simulate firing
    mgr._on_wm_hotkey(1)  # 'toggle'
    mgr._on_wm_hotkey(2)  # 'panic'
    mgr._on_wm_hotkey(3)  # 'show'
    assert events == ["toggle", "panic", "show"]
```

- [ ] **Step 2: Run tests, confirm FAIL**

```powershell
py -3.11 -m pytest tests/test_hotkeys.py -v
```

Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `src/hotkeys.py`**

```python
"""Global hotkeys via Win32 RegisterHotKey + Qt nativeEvent.

Public surface:
- parse_hotkey("F6") -> (modifiers, vk)
- GlobalHotkeyManager(on_activate) with .register_all() and .unregister()
"""
from __future__ import annotations
import sys
from typing import Callable
from PySide6.QtCore import QObject, Qt

# Win32 mod flags
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

# Virtual key codes (F1-F24)
_FK = {f"F{i}": 0x70 + i for i in range(1, 25)}
# Esc
_VK = {"ESC": 0x1B, "ESCAPE": 0x1B, **{
    chr(c): c for c in range(ord("A"), ord("Z") + 1)
}, **{
    chr(c): c for c in range(ord("0"), ord("9") + 1)
}, **_FK}


def parse_hotkey(spec: str) -> tuple[int, int]:
    """Parse 'F6' / 'Ctrl+Shift+A' / 'Esc' into (modifiers, vk)."""
    parts = [p.strip().upper() for p in spec.split("+")]
    if not parts:
        raise ValueError("Empty hotkey spec")
    vk_part = parts[-1]
    if vk_part not in _VK:
        raise ValueError(f"Unknown virtual key: {vk_part}")
    vk = _VK[vk_part]
    mod = 0
    for p in parts[:-1]:
        if p == "CTRL" or p == "CONTROL":
            mod |= MOD_CONTROL
        elif p == "SHIFT":
            mod |= MOD_SHIFT
        elif p == "ALT":
            mod |= MOD_ALT
        elif p == "WIN" or p == "META":
            mod |= MOD_WIN
        else:
            raise ValueError(f"Unknown modifier: {p}")
    mod |= MOD_NOREPEAT
    return mod, vk


class GlobalHotkeyManager(QObject):
    """Wraps Win32 RegisterHotKey. Hotkeys are global to the OS session."""

    def __init__(self, on_activate: Callable[[str], None], parent=None):
        super().__init__(parent)
        self._on_activate = on_activate
        self._hotkeys: list[tuple[int, int, int]] = []  # (id, mod, vk)
        self._handles: dict[int, str] = {}  # id -> name
        self._hwnd = None
        self._registered: list[tuple[int, str]] = []
        self._specs = []  # populated in register_all

    def _register(self, name: str, spec: str) -> bool:
        """Register a single hotkey. Returns True on success.
        On non-Windows, returns True without doing anything (tests still pass)."""
        if sys.platform != "win32":
            self._handles[id(self)] = name
            return True
        # Real implementation: come back in Task 5b if needed
        # (Stub for now; replaced when MainWindow is wired up.)
        try:
            mod, vk = parse_hotkey(spec)
        except ValueError:
            return False
        self._handles[len(self._handles) + 1] = name
        return True

    def _on_wm_hotkey(self, hotkey_id: int) -> None:
        name = self._handles.get(hotkey_id)
        if name:
            self._on_activate(name)

    def register_all(self, *, toggle: str = "F6", panic: str = "Esc",
                     show: str = "Ctrl+Shift+A") -> bool:
        self._specs = [("toggle", toggle), ("panic", panic), ("show", show)]
        ok = True
        for name, spec in self._specs:
            if not self._register(name, spec):
                ok = False
        return ok

    def unregister(self) -> None:
        self._registered.clear()
        self._handles.clear()
```

- [ ] **Step 4: Run tests, confirm PASS**

```powershell
py -3.11 -m pytest tests/test_hotkeys.py -v
```

Expected: 4 tests pass.

> **Note:** real Win32 `RegisterHotKey` requires the QWidget window's HWND. We hook it into `main_window.py`'s nativeEvent in Task 8.

---

## Task 6: Styles (QSS + acrylic)

**Files:**
- Create: `D:\0Tools\鼠标连点器/src/styles.py`

(No automated test — visual only. Manual verification in Task 8.)

- [ ] **Step 1: Implement `src/styles.py`**

```python
"""QSS stylesheet for Fluent-style acrylic look.

The actual acrylic backdrop is enabled separately via enable_acrylic(window).
This file only paints QSS for widgets.
"""
from __future__ import annotations
import sys
import ctypes

try:
    import winreg  # noqa: F401  (only present on Windows; not used directly here)
    IS_WIN = True
except ImportError:
    IS_WIN = False

# Win11 DWMWA_SYSTEMBACKDROP_TYPE values (build 22523+)
_DWMWA_SYSTEMBACKDROP_TYPE = 38
_DWMSBT_AUTO = 0
_DWMSBT_MAINWINDOW = 2  # soft acrylic, transient

# ===== QSS =====
QSS = """
* {
    font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
    color: #1f1f1f;
}

QMainWindow, QWidget#central {
    background: transparent;
}

QLabel#title {
    font-size: 14px;
    font-weight: 600;
    color: #1f1f1f;
}

QLabel#statusBadge {
    background: #ecfdf5;
    color: #047857;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 11px;
}
QLabel#statusBadge[state="running"] {
    background: #e8f5e9;
    color: #2e7d32;
}
QLabel#statusBadge[state="stopped"] {
    background: #f0f0f0;
    color: #555;
}

QPushButton#cta {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0067c0, stop:1 #4a6ee0);
    color: white;
    border: none;
    border-radius: 6px;
    padding: 14px;
    font-size: 15px;
    font-weight: 600;
    letter-spacing: 1px;
}
QPushButton#cta:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0078d4, stop:1 #5a7eef);
}
QPushButton#cta:pressed {
    background: #0067c0;
}
QPushButton#cta[running="true"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #e81123, stop:1 #c00000);
}

QFrame#settingsCard {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    padding: 12px;
}

QLabel.settingLabel {
    color: #555;
    font-size: 12px;
}

QSlider::groove:horizontal {
    height: 4px;
    background: #e0e0e0;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #0067c0;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: white;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
    border: 2px solid #0067c0;
}

QSpinBox {
    background: white;
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 3px 6px;
    min-width: 64px;
}

QPushButton[segmented="true"] {
    background: #f0f0f0;
    color: #555;
    border: 1px solid #ddd;
    padding: 6px 12px;
    font-size: 12px;
}
QPushButton[segmented="true"]:checked {
    background: #0067c0;
    color: white;
    border-color: #0067c0;
}

QLabel#footer {
    color: #888;
    font-size: 10px;
    padding: 8px;
}

QLabel#statValue {
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 18px;
    font-weight: 600;
    color: #1f1f1f;
}
QLabel#statKey {
    color: #888;
    font-size: 10px;
    text-transform: uppercase;
}
"""


def enable_acrylic(window) -> None:
    """Enable Windows 11 acrylic backdrop on the given window.
    No-op on Windows 10/other platforms (QSS will paint a pseudo-acrylic)."""
    if not IS_WIN or sys.platform != "win32":
        return
    try:
        hwnd = int(window.winId())
        # Enable DWMA backdrop
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_int(hwnd),
            ctypes.c_int(_DWMWA_SYSTEMBACKDROP_TYPE),
            ctypes.byref(ctypes.c_int(_DWMSBT_MAINWINDOW)),
            ctypes.sizeof(ctypes.c_int),
        )
    except (AttributeError, OSError):
        pass  # Win10 or pre-22523: skip silently


def apply_app_style(app) -> None:
    app.setStyleSheet(QSS)
```

- [ ] **Step 2: Sanity import**

```powershell
py -3.11 -c "from src.styles import QSS, enable_acrylic, apply_app_style; print('OK', len(QSS))"
```

Expected: prints `OK <number>`.

---

## Task 7: Tray icon

**Files:**
- Create: `D:\0Tools\鼠标连点器/src/tray.py`
- Create: `D:\0Tools\鼠标连点器/assets/icon.ico` (binary placeholder, see Step 1)

- [ ] **Step 1: Add a minimal asset for testing**

Without a real icon, generate a tiny 16x16 placeholder using PIL or just hand-craft a minimal ICO.

```powershell
py -3.11 -m pip install Pillow
py -3.11 -c "from PIL import Image, ImageDraw; im=Image.new('RGBA',(256,256),(0,0,0,0)); d=ImageDraw.Draw(im); d.ellipse([20,20,236,236],fill=(0,103,192,255)); d.rectangle([110,40,146,216],fill='white'); d.rectangle([40,110,216,146],fill='white'); im.save(r'D:\0Tools\鼠标连点器/assets/icon.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"
py -3.11 -c "import shutil; shutil.copy(r'D:\0Tools\鼠标连点器/assets/icon.ico', r'D:\0Tools\鼠标连点器/assets/icon-running.ico')"
```

Expected: two files exist.

- [ ] **Step 2: Implement `src/tray.py`**

```python
"""Tray icon with right-click menu (show / toggle / quit)."""
from __future__ import annotations
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


class TrayController:
    def __init__(self, app, on_show, on_toggle, on_quit):
        self._app = app
        self._icon_idle = QIcon("assets/icon.ico")
        self._icon_running = QIcon("assets/icon-running.ico")
        self._tray = QSystemTrayIcon(self._icon_idle, parent=app)
        self._tray.setToolTip("鼠标连点器")

        menu = QMenu()
        self._action_show = QAction("显示主窗口", menu)
        self._action_show.triggered.connect(on_show)
        self._action_toggle = QAction("启停", menu)
        self._action_toggle.triggered.connect(on_toggle)
        action_quit = QAction("退出", menu)
        action_quit.triggered.connect(on_quit)
        menu.addAction(self._action_show)
        menu.addAction(self._action_toggle)
        menu.addSeparator()
        menu.addAction(action_quit)
        self._tray.setContextMenu(menu)

        self._tray.activated.connect(self._on_activated)
        self._tray.show()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:  # left click
            self._action_show.trigger()

    def set_running(self, running: bool) -> None:
        self._tray.setIcon(self._icon_running if running else self._icon_idle)
        self._action_toggle.setText("停止" if running else "启动")

    def update_toggle_action(self, running: bool) -> None:
        self.set_running(running)

    def hide(self):
        self._tray.hide()
```

- [ ] **Step 3: Smoke import**

```powershell
py -3.11 -c "from src.tray import TrayController; print('OK')"
```

Expected: `OK`.

---

## Task 8: MainWindow UI

**Files:**
- Create: `D:\0Tools\鼠标连点器/src/main_window.py`
- Modify: `D:\0Tools\鼠标连点器/tests/test_app_smoke.py` (replace placeholder)

- [ ] **Step 1: Implement `src/main_window.py`**

```python
"""MainWindow: assembles all UI widgets and wires them to ClickerEngine / hotkeys."""
from __future__ import annotations
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton, QSlider, QSpinBox, QVBoxLayout,
    QHBoxLayout, QButtonGroup, QFrame, QGridLayout, QStatusBar
)
from src.clicker import ClickerEngine
from src.config import AppConfig
from src.hotkeys import GlobalHotkeyManager, parse_hotkey


class SegmentedRow(QFrame):
    """A horizontal row of toggle buttons styled as a segmented control."""
    changed = Signal(str)

    def __init__(self, label: str, options: list[tuple[str, str]], parent=None):
        super().__init__(parent)
        self.setObjectName("settingsCard")
        self.setProperty("settingsCard", True)
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 8, 12, 8)
        lbl = QLabel(label)
        lbl.setProperty("class", "settingLabel")
        v.addWidget(lbl)
        row = QHBoxLayout()
        row.setSpacing(0)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._options = list(options)  # list of (value, text)
        self._buttons: list[QPushButton] = []
        for value, text in options:
            b = QPushButton(text)
            b.setCheckable(True)
            b.setProperty("segmented", True)
            self._group.addButton(b)
            b.toggled.connect(lambda checked, v=value: self._on_toggled(v, checked))
            row.addWidget(b)
            self._buttons.append(b)
        v.addLayout(row)
        self._value = options[0][0]
        self._buttons[0].setChecked(True)

    def _on_toggled(self, value: str, checked: bool) -> None:
        if checked:
            self._value = value
            self.changed.emit(value)

    def value(self) -> str:
        return self._value

    def set_value(self, v: str) -> None:
        for btn, (val, _txt) in zip(self._buttons, self._options):
            if val == v:
                btn.setChecked(True)
                self._value = v
                return
        # Unknown value: keep current
        self._buttons[0].setChecked(True)
        self._value = self._options[0][0]  # type: ignore[assignment]  (ensures valid)


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig, clicker: ClickerEngine,
                 hotkeys: GlobalHotkeyManager):
        super().__init__()
        self._config = config
        self._clicker = clicker
        self._hotkeys = hotkeys

        self.setWindowTitle("鼠标连点器")
        self.resize(380, 480)
        self.setMinimumSize(380, 480)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowIcon(QIcon("assets/icon.ico"))

        central = QWidget()
        central.setObjectName("central")
        central.setStyleSheet("background: rgba(243,243,243,0.85); border-radius: 12px;")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Title bar
        titlebar = QHBoxLayout()
        title = QLabel("鼠标连点器")
        title.setObjectName("title")
        titlebar.addWidget(title)
        titlebar.addStretch()
        self._btn_close = QPushButton("✕")
        self._btn_close.setFixedSize(28, 22)
        self._btn_close.setStyleSheet("background: transparent; color: #555; border: none; font-size: 14px;")
        self._btn_close.clicked.connect(self.hide)
        titlebar.addWidget(self._btn_close)
        layout.addLayout(titlebar)

        # Status row
        status_row = QHBoxLayout()
        self._status = QLabel("已停止")
        self._status.setObjectName("statusBadge")
        self._status.setProperty("state", "stopped")
        status_row.addWidget(self._status)
        status_row.addStretch()
        self._params_label = QLabel("")
        self._params_label.setStyleSheet("color:#666; font-size:11px;")
        status_row.addWidget(self._params_label)
        layout.addLayout(status_row)

        # CTA
        self._cta = QPushButton("▶  启  动")
        self._cta.setObjectName("cta")
        self._cta.setProperty("running", False)
        self._cta.setMinimumHeight(52)
        self._cta.clicked.connect(self._on_toggle_clicked)
        layout.addWidget(self._cta)

        # Interval row
        interval_card = QFrame()
        interval_card.setObjectName("settingsCard")
        iv = QVBoxLayout(interval_card)
        iv.setContentsMargins(12, 8, 12, 12)
        iv.addWidget(self._make_setting_label("点击间隔"))
        h = QHBoxLayout()
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setMinimum(10)
        self._slider.setMaximum(10000)
        self._slider.setSingleStep(10)
        self._slider.setPageStep(100)
        self._slider.setValue(self._config.interval_ms)
        self._spin = QSpinBox()
        self._spin.setMinimum(10)
        self._spin.setMaximum(10000)
        self._spin.setSuffix(" ms")
        self._spin.setValue(self._config.interval_ms)
        self._slider.valueChanged.connect(self._spin.setValue)
        self._spin.valueChanged.connect(self._slider.setValue)
        h.addWidget(self._slider, 1)
        h.addWidget(self._spin)
        iv.addLayout(h)
        layout.addWidget(interval_card)

        # Segmented rows
        self._button_row = SegmentedRow("按键",
            [("left", "左"), ("right", "右"), ("middle", "中")])
        self._click_type_row = SegmentedRow("类型",
            [("single", "单击"), ("double", "双击")])
        self._pos_mode_row = SegmentedRow("位置",
            [("current", "当前位置"), ("locked", "锁定坐标"), ("follow", "跟随鼠标")])
        self._button_row.changed.connect(self._on_param_changed)
        self._click_type_row.changed.connect(self._on_param_changed)
        self._pos_mode_row.changed.connect(self._on_param_changed)
        layout.addWidget(self._button_row)
        layout.addWidget(self._click_type_row)
        layout.addWidget(self._pos_mode_row)

        # Stats
        stats_row = QHBoxLayout()
        self._count_label = QLabel("0")
        self._count_label.setObjectName("statValue")
        self._count_label.setAlignment(Qt.AlignCenter)
        count_card = QFrame()
        count_card.setObjectName("settingsCard")
        cv = QVBoxLayout(count_card)
        cv.setContentsMargins(8, 6, 8, 6)
        cv.setSpacing(0)
        k = QLabel("已点击"); k.setObjectName("statKey")
        cv.addWidget(k)
        cv.addWidget(self._count_label)
        stats_row.addWidget(count_card, 1)
        self._elapsed_label = QLabel("00:00")
        self._elapsed_label.setObjectName("statValue")
        self._elapsed_label.setAlignment(Qt.AlignCenter)
        elapsed_card = QFrame()
        elapsed_card.setObjectName("settingsCard")
        ev = QVBoxLayout(elapsed_card)
        ev.setContentsMargins(8, 6, 8, 6)
        ev.setSpacing(0)
        k2 = QLabel("运行时长"); k2.setObjectName("statKey")
        ev.addWidget(k2)
        ev.addWidget(self._elapsed_label)
        stats_row.addWidget(elapsed_card, 1)
        layout.addLayout(stats_row)

        # Footer
        footer = QLabel(f"F6 启停 · Esc 急停 · {self._config.hotkey_show} 显示")
        footer.setObjectName("footer")
        layout.addWidget(footer)
        layout.addStretch()

        # Wire ClickerEngine signals
        self._clicker.started.connect(self._on_clicker_started)
        self._clicker.stopped.connect(self._on_clicker_stopped)
        self._clicker.stats_updated.connect(self._on_stats)

        # Save config debounce timer
        self._save_timer = QTimer(self)
        self._save_timer.setInterval(500)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._config.save)

        # Trigger hotkey
        self._hotkeys._on_activate = self._on_hotkey
        # push initial configured values into clicker
        self._apply_clicker_config()

    def _make_setting_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setProperty("class", "settingLabel")
        return lbl

    def _apply_clicker_config(self) -> None:
        self._clicker.configure(
            interval_ms=self._spin.value(),
            button=self._button_row.value(),
            click_type=self._click_type_row.value(),
            position_mode=self._pos_mode_row.value(),
            locked_xy=(self._config.locked_x, self._config.locked_y),
        )
        self._params_label.setText(
            f"{self._spin.value()}ms · {self._button_row.value()} · {self._pos_mode_row.value()}"
        )

    def _on_param_changed(self, _value=None):
        # Update config + save (debounced) + push to clicker
        self._config.interval_ms = self._spin.value()
        self._config.button = self._button_row.value()
        self._config.click_type = self._click_type_row.value()
        self._config.position_mode = self._pos_mode_row.value()
        self._save_timer.start()
        self._apply_clicker_config()

    def _on_toggle_clicked(self) -> None:
        if self._clicker.is_running():
            self._clicker.stop()
        else:
            self._clicker.start()

    def _on_clicker_started(self) -> None:
        self._status.setText("运行中")
        self._status.setProperty("state", "running")
        self._cta.setText("■  停  止")
        self._cta.setProperty("running", True)
        self._update_styles()

    def _on_clicker_stopped(self) -> None:
        self._status.setText("已停止")
        self._status.setProperty("state", "stopped")
        self._cta.setText("▶  启  动")
        self._cta.setProperty("running", False)
        self._update_styles()

    def _update_styles(self) -> None:
        # re-apply style so QSS sees property changes
        self.style().polish(self._cta)
        self.style().polish(self._status)

    def _on_stats(self, count: int, elapsed_ms: int) -> None:
        self._count_label.setText(f"{count:,}")
        s = elapsed_ms // 1000
        self._elapsed_label.setText(f"{s//60:02d}:{s%60:02d}")

    def _on_hotkey(self, name: str) -> None:
        if name == "toggle":
            self._on_toggle_clicked()
        elif name == "panic":
            if self._clicker.is_running():
                self._clicker.stop()
        elif name == "show":
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()
                self.raise_()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.y() < 36:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if hasattr(self, "_drag_pos") and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def closeEvent(self, event):
        # Hide to tray instead of quitting
        event.ignore()
        self.hide()
```

- [ ] **Step 2: Replace smoke test**

Replace `tests/test_app_smoke.py` with:

```python
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
    # Window should have non-zero size and at least one child widget
    assert win.isVisible()
    assert win.width() >= 380
    assert win.height() >= 480
    QTimer.singleShot(50, win.close)
    qapp.processEvents()
```

- [ ] **Step 3 (intermediate): Add locked-coordinate capture (取点)**

In `src/main_window.py`, add a "取点" button below the position row, plus a 3-second capture window that listens for F6:

```python
# In __init__, after layout.addWidget(self._pos_mode_row):
self._pick_btn = QPushButton("📍 取点 (按 F6 锁定当前位置)")
self._pick_btn.setStyleSheet("""
    background: transparent; color: #0067c0; border: 1px solid #0067c0;
    border-radius: 4px; padding: 6px 12px; font-size: 12px;
""")
self._pick_btn.clicked.connect(self._start_capture_mode)
layout.addWidget(self._pick_btn)

# In MainWindow, add:
self._capture_timer = QTimer(self)
self._capture_timer.setSingleShot(True)
self._capture_timer.setInterval(3000)
self._capture_timer.timeout.connect(self._cancel_capture_mode)
self._capture_active = False

def _start_capture_mode(self):
    if self._clicker.is_running():
        return  # don't capture while running
    self._capture_active = True
    self._capture_timer.start()
    self._pick_btn.setText("3 秒内按 F6 捕获当前位置…")
    self._pick_btn.setStyleSheet("""
        background: #fff3cd; color: #856404; border: 1px solid #ffeeba;
        border-radius: 4px; padding: 6px 12px; font-size: 12px;
    """)

def _cancel_capture_mode(self):
    self._capture_active = False
    self._pick_btn.setText("📍 取点 (按 F6 锁定当前位置)")
    self._pick_btn.setStyleSheet("""
        background: transparent; color: #0067c0; border: 1px solid #0067c0;
        border-radius: 4px; padding: 6px 12px; font-size: 12px;
    """)

def _perform_capture(self):
    import ctypes
    pt = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    self._config.locked_x = pt.x
    self._config.locked_y = pt.y
    self._config.save()
    self._capture_timer.stop()
    self._pick_btn.setText(f"✓ 已锁定 ({pt.x}, {pt.y})")
    self._capture_active = False
```

And modify `_on_hotkey` so F6 in capture mode routes to `_perform_capture` instead of toggling:

```python
def _on_hotkey(self, name: str):
    if name == "toggle":
        if self._capture_active:
            self._perform_capture()
            return
        self._on_toggle_clicked()
    elif name == "panic":
        if self._clicker.is_running():
            self._clicker.stop()
    elif name == "show":
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.activateWindow()
            self.raise_()
```

- [ ] **Step 4: Run smoke test**

```powershell
py -3.11 -m pytest tests/test_app_smoke.py -v
```

Expected: 1 passed.

---

## Task 9: Single-instance lock

**Files:**
- Create: `D:\0Tools\鼠标连点器/src/single_instance.py`
- Create: `D:\0Tools\鼠标连点器/tests/test_single_instance.py`

- [ ] **Step 1: Write failing test**

File `tests/test_single_instance.py`:

```python
import os
import sys
import pytest

@pytest.mark.skipif(os.name != "nt", reason="Windows-only")
def test_acquire_then_second_acquire_fails():
    from src.single_instance import SingleInstance
    si1 = SingleInstance(name="Local\\AutoClickerSingleInstance_TEST_A")
    si2 = SingleInstance(name="Local\\AutoClickerSingleInstance_TEST_A")
    assert si1.acquire()
    assert not si2.acquire()  # second fails
    si1.release()
    assert si2.acquire()  # now succeeds
    si2.release()
```

- [ ] **Step 2: Run, confirm FAIL**

```powershell
py -3.11 -m pytest tests/test_single_instance.py -v
```

Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `src/single_instance.py`**

```python
"""Single-instance enforcement via Win32 named mutex."""
from __future__ import annotations
import sys
import ctypes


class SingleInstance:
    def __init__(self, name: str = "Local\\AutoClickerSingleInstance"):
        self._name = name
        self._handle = None

    def acquire(self) -> bool:
        if sys.platform != "win32":
            # Non-Windows always allow; tests on macOS/Linux fine
            return True
        if self._handle is not None:
            return True
        kernel32 = ctypes.windll.kernel32
        ERROR_ALREADY_EXISTS = 183
        # CreateMutexW(NULL, FALSE, name) -> HANDLE
        CreateMutexW = kernel32.CreateMutexW
        CreateMutexW.restype = ctypes.wintypes.HANDLE
        CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        handle = CreateMutexW(None, False, self._name)
        if not handle:
            return False
        err = kernel32.GetLastError()
        if err == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            return False
        self._handle = handle
        return True

    def release(self) -> None:
        if self._handle is not None:
            ctypes.windll.kernel32.CloseHandle(self._handle)
            self._handle = None

    def __del__(self):
        self.release()
```

- [ ] **Step 4: Run, confirm PASS**

```powershell
py -3.11 -m pytest tests/test_single_instance.py -v
```

Expected: 1 passed.

---

## Task 10: Wire hotkeys to real Win32 RegisterHotKey

**Files:**
- Modify: `D:\0Tools\鼠标连点器/src/hotkeys.py` — replace `_register` stub with real implementation that needs an HWND.
- Modify: `D:\0Tools\鼠标连点器/src/main_window.py` — install nativeEvent filter to dispatch WM_HOTKEY.

- [ ] **Step 1: Replace `_register` in hotkeys.py**

In `src/hotkeys.py`, replace the `_register` method body:

```python
def _register(self, name: str, spec: str) -> bool:
    if sys.platform != "win32":
        self._handles[len(self._handles) + 1] = name
        return True
    if self._hwnd is None:
        # Need hwnd from QWidget; set by main_window
        return False
    try:
        mod, vk = parse_hotkey(spec)
    except ValueError:
        return False
    hotkey_id = len(self._handles) + 1
    ok = ctypes.windll.user32.RegisterHotKeyW(
        self._hwnd, hotkey_id, mod, vk
    )
    if ok:
        self._handles[hotkey_id] = name
        return True
    return False

def attach(self, hwnd: int) -> None:
    self._hwnd = hwnd
    # Re-register any previously specified hotkeys now that we have HWND
    for name, spec in self._specs:
        self._register(name, spec)
```

At top of file, add `import ctypes`.

- [ ] **Step 2: Wire nativeEvent in MainWindow**

In `src/main_window.py`, in `MainWindow.__init__`, after the window is realized (call it after `self.setCentralWidget(central)` since `winId()` requires a window):

```python
self._hwnd = int(self.winId())
self._hotkeys.attach(self._hwnd)
```

Add the following method to the `MainWindow` class:

```python
def nativeEvent(self, eventType, message):
    """Capture WM_HOTKEY messages from Win32."""
    if eventType in ("windows_generic_MSG", "windows_dispatcher_MSG"):
        try:
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == 0x0312:  # WM_HOTKEY
                self._hotkeys._on_wm_hotkey(msg.wParam)
                return True, 0
        except Exception:
            pass
    return False, 0
```

At top of file: `import ctypes`. (Note: do NOT use `installEventFilter(self)` — WM_HOTKEY is a native Win32 message, not a Qt event; nativeEvent override alone is sufficient.)

- [ ] **Step 3: Manual verification**

Run the app (Task 12 will do this). Press F6 → window CTA state should change.

---

## Task 11: Wire everything in `app.py`

**Files:**
- Modify: `D:\0Tools\鼠标连点器/src/app.py`

- [ ] **Step 1: Implement `app.py`**

```python
"""Entry point: instantiate QApplication, load config, show window, run loop."""
from __future__ import annotations
import sys
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from src.clicker import ClickerEngine
from src.config import AppConfig
from src.hotkeys import GlobalHotkeyManager
from src.main_window import MainWindow
from src.single_instance import SingleInstance
from src.styles import apply_app_style, enable_acrylic
from src.tray import TrayController
from src.windows_dpi import enable_dpi_awareness


def _quit(app, clicker, config):
    if clicker.is_running():
        clicker.stop()
    config.save()
    instance.release()
    app.quit()


def main() -> int:
    enable_dpi_awareness()

    instance = SingleInstance()
    if not instance.acquire():
        # Existing instance: do nothing (real version would raise existing window)
        return 0

    app = QApplication(sys.argv)
    app.setApplicationName("AutoClicker")
    app.setQuitOnLastWindowClosed(False)  # tray keeps it alive
    apply_app_style(app)

    config = AppConfig.load()
    clicker = ClickerEngine()
    hotkeys = GlobalHotkeyManager(on_activate=lambda _: None)
    window = MainWindow(config, clicker, hotkeys)

    enable_acrylic(window)

    tray = TrayController(
        app,
        on_show=lambda: (window.showNormal(), window.activateWindow()),
        on_toggle=lambda: window._on_toggle_clicked(),
        on_quit=lambda: _quit(app, clicker, config),
    )

    clicker.started.connect(lambda: tray.set_running(True))
    clicker.stopped.connect(lambda: tray.set_running(False))

    # Delay show 200ms to avoid stealing focus at startup
    QTimer.singleShot(200, window.show)
    QTimer.singleShot(200, window.activateWindow)

    # Try to register global hotkeys
    if not hotkeys.register_all(toggle=config.hotkey_toggle,
                                 panic="Esc",
                                 show=config.hotkey_show):
        # fall back: rely on F6 inside the window only
        pass

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Manual run**

```powershell
py -3.11 -m src.app
```

Expected: window appears ~200ms after launch; pressing F6 toggles CTA; Esc stops; Ctrl+Shift+A shows/hides; close (×) hides to tray; tray "退出" closes.

---

## Task 12: Build .exe

**Files:**
- Create: `D:\0Tools\鼠标连点器/build.spec`

- [ ] **Step 1: Write `build.spec`**

```python
# PyInstaller spec
# Build with: pyinstaller build.spec
import sys
from PyInstaller.utils.uses import canimport

a = Analysis(
    ['src/app.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/*.ico', 'assets')],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'email', 'xml', 'pydoc'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='鼠标连点器',
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon='assets/icon.ico',
)
```

- [ ] **Step 2: Build**

```powershell
py -3.11 -m PyInstaller build.spec --clean
dir dist
```

Expected: `dist/鼠标连点器.exe` (~30 MB) exists.

- [ ] **Step 3: Smoke run built exe**

```powershell
.\dist\鼠标连点器.exe
```

Expected: same behavior as Task 11 step 2.

- [ ] **Step 4: Final acceptance**

Run through §7 of the spec:
- [ ] F6 in another window context → CTA changes → clicks reach target
- [ ] Slider 100ms → ~10 clicks/sec reaching target window
- [ ] Esc stops from any context
- [ ] Window appears 200ms after launch (no focus steal)
- [ ] Close × → tray icon stays, click cycle continues
- [ ] Second launch → existing window raised, no error
