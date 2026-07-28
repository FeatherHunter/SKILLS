"""Global hotkeys via two layers:
1. WH_KEYBOARD_LL low-level keyboard hook via `keyboard` library (primary) —
   intercepts keys BEFORE Windows dispatches them. Cannot be blocked by
   other apps registering the same combo (RegisterHotKey is global-uniq;
   WH_KEYBOARD_LL is global-per-process).
2. Win32 RegisterHotKey as a fallback (kept for diagnostics + older systems).
"""
from __future__ import annotations
import ctypes
import sys
import threading
from typing import Callable
from PySide6.QtCore import QAbstractNativeEventFilter, QObject
from PySide6.QtWidgets import QApplication

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000


def _log_to_file(msg: str) -> None:
    """Append a diagnostic line to %TEMP%/autoclicker_hotkey.log."""
    try:
        from pathlib import Path
        import os
        log = Path(os.environ.get("TEMP", ".")) / "autoclicker_hotkey.log"
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"{msg}\n")
    except OSError:
        pass

_FK = {f"F{i}": 0x70 + (i - 1) for i in range(1, 25)}
# Extended F-keys (F13-F24) — virtually never used by apps, lowest conflict.
_FK.update({f"F{i}": 0x7B + (i - 12) for i in range(13, 25)})
_VK = {"ESC": 0x1B, "ESCAPE": 0x1B}
_VK.update({chr(c): c for c in range(ord("A"), ord("Z") + 1)})
_VK.update({chr(c): c for c in range(ord("0"), ord("9") + 1)})
_VK.update(_FK)
# Backtick / tilde (key below Esc, left of 1). Single-key toggle hotkey,
# no F-keys per user request. Conflicts mainly with terminals / Vim.
_VK["`"] = 0xC0  # VK_OEM_3


def parse_hotkey(spec: str) -> tuple[int, int]:
    parts = [p.strip().upper() for p in spec.split("+")]
    if not parts:
        raise ValueError("Empty hotkey spec")
    vk_part = parts[-1]
    if vk_part not in _VK:
        raise ValueError(f"Unknown virtual key: {vk_part}")
    vk = _VK[vk_part]
    mod = 0
    for p in parts[:-1]:
        if p in ("CTRL", "CONTROL"):
            mod |= MOD_CONTROL
        elif p == "SHIFT":
            mod |= MOD_SHIFT
        elif p == "ALT":
            mod |= MOD_ALT
        elif p in ("WIN", "META"):
            mod |= MOD_WIN
        else:
            raise ValueError(f"Unknown modifier: {p}")
    mod |= MOD_NOREPEAT
    return mod, vk


def _spec_to_keyboard_str(spec: str) -> str:
    """Translate 'Ctrl+Shift+Alt+C' to the format the `keyboard` lib expects.
    The keyboard lib uses lowercase with the literal key name; modifiers
    are 'ctrl', 'alt', 'shift', 'win'. The trailing key is the literal char
    (a-z, 0-9), function name (f1-f24), or named key (esc, tab, ...)."""
    s = spec.lower()
    # Order matters: 'ctrl' before 'control'; alphabetical otherwise ok.
    # keyboard lib accepts both spellings — leave as-is.
    return s


class _NativeHotkeyFilter(QAbstractNativeEventFilter):
    """Receives WM_HOTKEY messages for any top-level window in this process.
    Installed on QApplication so it sees all native events regardless of which
    widget (if any) currently has focus or is visible. Acts as a fallback
    if the `keyboard` library hook is unavailable."""

    WM_HOTKEY = 0x0312

    def __init__(self, on_hotkey: Callable[[int], None]):
        super().__init__()
        self._on_hotkey = on_hotkey

    def nativeEventFilter(self, eventType, message):
        if eventType not in ("windows_generic_MSG", "windows_dispatcher_MSG"):
            return False
        try:
            msg = ctypes.wintypes.MSG.from_address(int(message))
        except (TypeError, ValueError):
            return False
        if msg.message != self.WM_HOTKEY:
            return False
        self._on_hotkey(msg.wParam)
        return True


class GlobalHotkeyManager(QObject):
    """Wraps Win32 RegisterHotKey + keyboard lib WH_KEYBOARD_LL hook."""

    def __init__(self, on_activate: Callable[[str], None], parent=None):
        super().__init__(parent)
        self._on_activate = on_activate
        self._handles: dict[int, str] = {}
        self._hwnd = None
        self._specs: list[tuple[str, str]] = []
        self._failed: set[str] = set()
        self._filter: _NativeHotkeyFilter | None = None
        self._kb_hooks: list = []  # keyboard library handles to remove on unregister

    def _register(self, name: str, spec: str) -> bool:
        if sys.platform != "win32":
            self._handles[len(self._handles) + 1] = name
            return True
        if self._hwnd is None:
            return False
        # PRIMARY PATH: `keyboard` library WH_KEYBOARD_LL hook. Cannot be
        # preempted by other apps' RegisterHotKey. Fires regardless of
        # which window has focus.
        ok = self._register_via_keyboard_lib(name, spec)
        if ok:
            hotkey_id = len(self._handles) + 1
            self._handles[hotkey_id] = name
            return True
        # FALLBACK PATH: Win32 RegisterHotKey. May fail if another app has
        # the same combo, but doesn't hurt to try.
        try:
            mod, vk = parse_hotkey(spec)
        except ValueError:
            self._failed.add(name)
            return False
        import ctypes
        hotkey_id = len(self._handles) + 1
        ok = ctypes.windll.user32.RegisterHotKey(self._hwnd, hotkey_id, mod, vk)
        if ok:
            self._handles[hotkey_id] = name
            return True
        self._failed.add(name)
        return False

    def _register_via_keyboard_lib(self, name: str, spec: str) -> bool:
        try:
            import keyboard  # type: ignore
        except (ImportError, OSError) as e:
            _log_to_file(f"[kb-hook] import failed: {e}")
            return False
        try:
            kb_spec = _spec_to_keyboard_str(spec)
        except (ValueError, AttributeError) as e:
            _log_to_file(f"[kb-hook] spec parse failed for {spec}: {e}")
            return False
        try:
            handle = keyboard.add_hotkey(
                kb_spec,
                lambda: self._on_activate(name),
                suppress=False,
                trigger_on_release=False,
            )
            self._kb_hooks.append((name, spec, handle))
            _log_to_file(f"[kb-hook] registered name={name} spec={spec}")
            return True
        except (ValueError, OSError) as e:
            _log_to_file(f"[kb-hook] add_hotkey failed name={name} spec={spec}: {e}")
            return False

    def _on_wm_hotkey(self, hotkey_id: int) -> None:
        name = self._handles.get(hotkey_id)
        if name:
            self._on_activate(name)

    def attach(self, hwnd: int) -> None:
        self._hwnd = hwnd
        # Install the application-wide native event filter once we have a
        # hwnd (i.e., once QApplication + window have been instantiated).
        if self._filter is None:
            app = QApplication.instance()
            if app is not None:
                self._filter = _NativeHotkeyFilter(self._on_wm_hotkey)
                app.installNativeEventFilter(self._filter)
        for name, spec in self._specs:
            self._register(name, spec)

    def register_all(self, *, toggle: str = "F6", panic: str = "Esc",
                     show: str = "Ctrl+Shift+A") -> bool:
        self._specs = [("toggle", toggle), ("panic", panic), ("show", show)]
        self._handles.clear()
        self._failed.clear()
        ok = True
        for i, (name, spec) in enumerate(self._specs, start=1):
            self._handles[i] = name
            if not self._register(name, spec):
                ok = False
        return ok

    def register_hotkey(self, name: str, spec: str) -> bool:
        """Register an additional hotkey bound to an existing action name.
        Returns True on success. Used to add backup hotkeys."""
        return self._register(name, spec)

    def failed_hotkeys(self) -> list[str]:
        """Return names (toggle/panic/show) that failed to register."""
        return list(self._failed)

    def unregister(self) -> None:
        if sys.platform == "win32" and self._hwnd is not None:
            import ctypes
            for hid in list(self._handles.keys()):
                ctypes.windll.user32.UnregisterHotKey(self._hwnd, hid)
        self._handles.clear()
        self._specs.clear()
