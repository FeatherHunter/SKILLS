import pytest
from src.hotkeys import GlobalHotkeyManager, parse_hotkey


def test_parse_hotkey_simple_letter():
    mod, vk = parse_hotkey("F6")
    assert vk == 0x75
    assert mod == 0x4000


def test_parse_hotkey_f13_extended():
    """F13 is the lowest-conflict toggle hotkey — verify it parses correctly."""
    mod, vk = parse_hotkey("F13")
    assert vk == 0x7C  # VK_F13
    assert mod == 0x4000


def test_parse_hotkey_backtick():
    """Backtick (single-key toggle, no F-keys per user preference)."""
    mod, vk = parse_hotkey("`")
    assert vk == 0xC0  # VK_OEM_3
    assert mod == 0x4000


def test_parse_hotkey_ctrl_shift_alt_c():
    """4-key combo toggle hotkey per user request. Low conflict probability."""
    mod, vk = parse_hotkey("Ctrl+Shift+Alt+C")
    # MOD_CONTROL | MOD_SHIFT | MOD_ALT | MOD_NOREPEAT
    assert (mod & 0x0002) and (mod & 0x0004) and (mod & 0x0001) and (mod & 0x4000)
    assert vk == ord("C")


def test_parse_hotkey_combo():
    mod, vk = parse_hotkey("Ctrl+Shift+A")
    assert (mod & 0x0002) and (mod & 0x0004)
    assert vk == ord("A")
    assert (mod & 0x4000)


def test_parse_hotkey_invalid_raises():
    with pytest.raises(ValueError):
        parse_hotkey("Garbage")


def test_manager_emits_signals_when_triggered(monkeypatch):
    events = []
    mgr = GlobalHotkeyManager(on_activate=lambda name: events.append(name))
    monkeypatch.setattr(mgr, "_register", lambda name, key: True)
    assert mgr.register_all()
    mgr._on_wm_hotkey(1)
    mgr._on_wm_hotkey(2)
    mgr._on_wm_hotkey(3)
    assert events == ["toggle", "panic", "show"]
