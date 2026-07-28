"""App config: dataclass + JSON load/save at ~/.autoclicker/config.json."""
from __future__ import annotations
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


def _config_dir() -> Path:
    """Resolve user's config dir. Tries %USERPROFILE%/.autoclicker, falls back to %LOCALAPPDATA%."""
    try:
        base = Path(os.environ.get("USERPROFILE") or Path.home())
        d = base / ".autoclicker"
        d.mkdir(parents=True, exist_ok=True)
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
    button: str = "left"
    click_type: str = "single"
    position_mode: str = "follow"
    locked_x: int = 0
    locked_y: int = 0
    hotkey_toggle: str = "Ctrl+Shift+Alt+C"
    hotkey_show: str = "Ctrl+Shift+A"

    # Backup toggle hotkeys registered in addition to `hotkey_toggle`.
    # If the primary hotkey is captured by another app (e.g. AutoHotkey,
    # corporate software), at least one of these will likely be free.
    # All are 4-key combos that almost no app uses.
    # Stored as list (not tuple) for clean JSON round-trip.
    hotkey_toggle_backups: list[str] = field(default_factory=lambda: [
        "Ctrl+Alt+F12",
        "Ctrl+Alt+Pause",
        "Ctrl+Shift+F12",
    ])

    def __post_init__(self):
        if self.button not in ("left", "right", "middle"):
            self.button = "left"
        if self.click_type not in ("single", "double"):
            self.click_type = "single"
        if self.position_mode not in ("current", "follow"):
            self.position_mode = "follow"
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
            try:
                path.rename(path.with_suffix(".json.bak"))
            except OSError:
                pass
            return cls()


def config_path() -> Path:
    return _config_dir() / "config.json"
