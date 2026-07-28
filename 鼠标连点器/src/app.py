"""Entry point: instantiate QApplication, load config, show window, run loop."""
from __future__ import annotations
import os
import sys
import traceback
from pathlib import Path

# Install crash logger FIRST so even import errors get logged.
def _log_path() -> Path:
    return Path(os.environ.get("TEMP", ".")) / "autoclicker_crash.log"


def _log(msg: str) -> None:
    try:
        with open(_log_path(), "a", encoding="utf-8") as f:
            f.write(f"[{os.getpid()}] {msg}\n")
    except OSError:
        pass


def _log_excepthook(exc_type, exc_value, exc_tb):
    try:
        log = _log_path()
        log.write_text(
            "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
            encoding="utf-8",
        )
    except OSError:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = _log_excepthook
_log(f"startup pid={os.getpid()} argv={sys.argv}")

# Imports below may fail (missing DLL, bad install) — those failures are now logged.
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

_log("imports loaded")

from src.clicker import ClickerEngine
from src.config import AppConfig
from src.hotkeys import GlobalHotkeyManager
from src.tray import TrayController
from src.main_window import MainWindow
from src.single_instance import SingleInstance, find_existing_window_hwnd
from src.styles import apply_app_style, enable_acrylic
from src.windows_dpi import enable_dpi_awareness


def _quit(app, clicker, config, instance, indicator=None):
    if clicker.is_running():
        clicker.stop()
    config.save()
    instance.release()
    app.quit()


def _raise_existing_window() -> None:
    """Try to bring existing instance's main window to front.
    Reads HWND published by first instance to %TEMP%/autoclicker.hwnd.
    Falls back to brute-force EnumWindows if file missing/stale.
    """
    import ctypes
    hwnd = None
    # Preferred: read published HWND
    try:
        hwnd_path = Path(os.environ.get("TEMP", ".")) / "autoclicker.hwnd"
        if hwnd_path.exists():
            val = int(hwnd_path.read_text(encoding="utf-8").strip())
            if val > 0 and ctypes.windll.user32.IsWindow(val):
                hwnd = val
    except (OSError, ValueError):
        pass

    # Fallback: brute-force EnumWindows (may pick wrong window if other apps
    # have >200x200 visible windows — only used if published HWND is missing)
    if hwnd is None:
        hwnd = find_existing_window_hwnd()

    if hwnd:
        SW_RESTORE = 9
        if ctypes.windll.user32.IsIconic(hwnd):
            ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
        ctypes.windll.user32.SetForegroundWindow(hwnd)


def main() -> int:
    enable_dpi_awareness()
    _log("dpi awareness set")

    instance = SingleInstance()
    if not instance.acquire():
        _log("second instance, raising existing")
        _raise_existing_window()
        return 0
    _log("single instance acquired")

    app = QApplication(sys.argv)
    app.setApplicationName("AutoClicker")
    app.setQuitOnLastWindowClosed(False)
    apply_app_style(app)
    _log("QApplication created")

    config = AppConfig.load()
    clicker = ClickerEngine()
    hotkeys = GlobalHotkeyManager(on_activate=lambda _: None)
    window = MainWindow(config, clicker, hotkeys)
    _log("widgets created")

    enable_acrylic(window)

    tray = TrayController(
        app,
        on_show=lambda: (window.showNormal(), window.activateWindow()),
        on_toggle=lambda: window._on_toggle_clicked(),
        on_quit=lambda: _quit(app, clicker, config, instance),
    )

    clicker.started.connect(lambda: tray.set_running(True))
    clicker.stopped.connect(lambda: tray.set_running(False))

    QTimer.singleShot(200, window.show)
    QTimer.singleShot(200, window.activateWindow)

    ok = hotkeys.register_all(toggle=config.hotkey_toggle,
                              panic="Esc",
                              show=config.hotkey_show)
    # Register backup toggle hotkeys so the user has alternatives if the
    # primary one is captured by another app. ALL of them trigger the
    # same `toggle` action, so any one of them works.
    if hasattr(config, "hotkey_toggle_backups"):
        for backup in config.hotkey_toggle_backups:
            hotkeys.register_hotkey("toggle", backup)
    if not ok:
        failed = hotkeys.failed_hotkeys()
        names = {"toggle": config.hotkey_toggle, "panic": "Esc",
                 "show": config.hotkey_show}
        msg = "部分热键被其他程序占用:\n" + "\n".join(
            f"  - {names.get(n, n)} ({n})" for n in failed
        ) + "\n\n可在托盘菜单退出后修改。"
        _log(f"hotkey registration FAILED: failed={failed}")
        try:
            from PySide6.QtWidgets import QSystemTrayIcon
            tray._tray.showMessage("鼠标连点器", msg, QSystemTrayIcon.Warning, 8000)
        except Exception:
            pass
        try:
            Path(os.environ.get("TEMP", "."), "autoclicker_hotkey.log").write_text(
                msg, encoding="utf-8"
            )
        except OSError:
            pass
        print(msg, file=sys.stderr)

    _log(f"hotkeys registered ok={ok}")
    _log(f"all handles: {hotkeys._handles}")
    _log(f"failed: {hotkeys.failed_hotkeys()}")
    _log(f"hwnd: {hotkeys._hwnd}")
    _log("entering event loop")

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
