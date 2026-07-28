"""Resource path helper for PyInstaller --onefile packaging.

When running from source, assets live in <project>/assets/.
When running from a PyInstaller bundle, they're unpacked to sys._MEIPASS/assets/.
This helper picks the right base directory so QIcon / setWindowIcon find them.
"""
from __future__ import annotations
import os
import sys


def resource_path(relative: str) -> str:
    """Resolve a project-relative path to an absolute filesystem path.

    `relative` is a forward-slash path like 'assets/icon.ico'. Returns the
    absolute path under either the PyInstaller bundle root (sys._MEIPASS)
    or the project root (two levels up from this file: src/ -> project root).
    """
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        # src/resources.py -> project root is parent of src/
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *relative.split("/"))
