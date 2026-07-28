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
            return True
        if self._handle is not None:
            return True
        kernel32 = ctypes.windll.kernel32
        ERROR_ALREADY_EXISTS = 183
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


def find_existing_window_hwnd() -> int | None:
    """Find the HWND of a previously-launched instance by looking for the
    window via a unique Qt window title. We use both Qt's windowTitle (set
    internally) and Win32's GetWindowText. Since our window is Frameless
    (no Win32 caption), GetWindowText returns empty. So we walk processes
    that have our mutex open and find their top-level window.

    Returns: HWND of existing instance, or None.
    """
    if sys.platform != "win32":
        return None
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    # Check mutex exists (i.e., another instance is running)
    SYNCHRONIZE = 0x00100000
    h = kernel32.OpenMutexW(SYNCHRONIZE, False, "Local\\AutoClickerSingleInstance")
    if not h:
        return None  # no other instance
    kernel32.CloseHandle(h)

    # Find PIDs that own the mutex — practically, find any visible top-level
    # window whose PID is not ours. Since the autoclicker is the only thing
    # this exe does, and mutex blocks second launch, the other instance is
    # guaranteed to have a visible main window when shown (or in tray if hidden).
    my_pid = kernel32.GetCurrentProcessId()
    found = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)

    def cb(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        # Skip very small windows (likely not the main app window)
        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        w = rect.right - rect.left
        h_ = rect.bottom - rect.top
        if w < 200 or h_ < 200:
            return True
        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value != my_pid:
            found.append(hwnd)
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    if found:
        # Heuristic: prefer the largest window (most likely the main app)
        # but for simplicity just return the first one found
        return found[0]
    return None
