import json
import os
import pytest
from src.config import AppConfig


def test_defaults():
    c = AppConfig()
    assert c.interval_ms == 100
    assert c.button == "left"
    assert c.click_type == "single"
    assert c.position_mode == "follow"
    assert c.locked_x == 0
    assert c.locked_y == 0
    assert c.hotkey_toggle == "Ctrl+Shift+Alt+C"
    assert c.hotkey_show == "Ctrl+Shift+A"


def test_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config._config_dir", lambda: tmp_path)
    c = AppConfig(interval_ms=500, button="right", click_type="double",
                  position_mode="locked", locked_x=400, locked_y=300,
                  hotkey_toggle="F8", hotkey_show="Ctrl+Alt+W",
                  hotkey_toggle_backups=["X", "Y"])
    c.save()
    assert (tmp_path / "config.json").exists()
    loaded = AppConfig.load()
    assert loaded == c


def test_load_missing_returns_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config._config_dir", lambda: tmp_path)
    c = AppConfig.load()
    assert c == AppConfig()


def test_load_corrupt_returns_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config._config_dir", lambda: tmp_path)
    (tmp_path / "config.json").write_text("not valid json {{{")
    c = AppConfig.load()
    assert c == AppConfig()
    assert (tmp_path / "config.json.bak").exists()


def test_interval_validation():
    c = AppConfig(interval_ms=10)
    assert c.interval_ms == 10
    c = AppConfig(interval_ms=5)
    assert c.interval_ms == 10
    c = AppConfig(interval_ms=99999)
    assert c.interval_ms == 10000
