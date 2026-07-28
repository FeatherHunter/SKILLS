"""Windows DPI awareness + screen clamping helpers."""
import ctypes
import sys


def enable_dpi_awareness() -> None:
    """Process DPI awareness. We use SYSTEM_AWARE (-2) rather than
    PER_MONITOR_AWARE_V2 (-4) for one specific reason: the cursor indicator
    window needs to track the mouse across monitors. With per-monitor DPI,
    Qt interprets window positions in logical (per-monitor DPI) units while
    GetCursorPos returns physical pixels — leading to a mismatch on mixed-DPI
    multi-monitor setups where the indicator appears off by the DPI ratio.

    SYSTEM_AWARE makes Qt use system-DPI coordinates consistently across
    monitors, matching GetCursorPos. The tradeoff is that the main window
    may render slightly less crisp on high-DPI monitors (Windows does
    bitmap stretching instead of letting Qt do per-monitor scaling). For
    our compact UI, this is acceptable."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(-2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass


def clamp_to_screen(x: int, y: int, screen_w: int, screen_h: int) -> tuple[int, int]:
    """Clamp a screen coordinate to [0, max-1] range."""
    return (max(0, min(x, screen_w - 1)), max(0, min(y, screen_h - 1)))
