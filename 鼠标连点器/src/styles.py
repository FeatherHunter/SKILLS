"""Per-widget QSS for window. Per-button styles are set directly via setStyleSheet()
because Qt's QSS class selectors are unreliable in PySide6 6.11."""
from __future__ import annotations
import sys
import ctypes

_DWMWA_SYSTEMBACKDROP_TYPE = 38
_DWMSBT_MAINWINDOW = 2

QSS = """
* {
    font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
    color: #1a1a1a;
}

QMainWindow, QWidget#central {
    background: transparent;
}

QLabel#title {
    font-size: 15px;
    font-weight: 600;
    color: #1a1a1a;
}

QFrame#settingsCard {
    background: white;
    border: 1px solid #e8eaef;
    border-radius: 8px;
}

QLabel.settingLabel {
    color: #888;
    font-size: 11px;
    font-weight: 500;
    padding: 2px 4px;
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
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 3px 6px;
    min-width: 64px;
}

QLabel#footer {
    color: #aaa;
    font-size: 11px;
    padding: 4px 0;
}

QLabel#statValue {
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 18px;
    font-weight: 700;
    color: #1a1a1a;
}
QLabel#statKey {
    color: #888;
    font-size: 10px;
    font-weight: 500;
}
"""


def enable_acrylic(window) -> None:
    """Enable Windows 11 acrylic backdrop on the given window.
    On Windows 10 / older versions: no-op (QSS paints a soft gradient fallback)."""
    if sys.platform != "win32":
        return
    try:
        hwnd = int(window.winId())
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_int(hwnd),
            ctypes.c_int(_DWMWA_SYSTEMBACKDROP_TYPE),
            ctypes.byref(ctypes.c_int(_DWMSBT_MAINWINDOW)),
            ctypes.sizeof(ctypes.c_int),
        )
    except (AttributeError, OSError):
        pass


def paint_frosted_fallback(window) -> None:
    """Fallback frosted look on Win10 / unsupported DWM. Paint a soft gradient
    with subtle noise via QSS on the central widget."""
    grad = (
        "background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
        " stop:0 #f3f6fb, stop:0.5 #eaf0f8, stop:1 #dde7f3);"
    )
    window.findChild(type(window.centralWidget()))  # no-op; keep import safe
    cw = window.centralWidget()
    if cw:
        existing = cw.styleSheet() or ""
        # Don't override if user already styled; just append gradient layer via object
        cw.setStyleSheet(existing + grad)


def apply_app_style(app) -> None:
    app.setStyleSheet(QSS)