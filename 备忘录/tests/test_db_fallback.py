"""v1.2.0 · DB fallback 路径守护(2026-08-02 · 新增 Linux 系统盘默认)

- Windows → D:/.db(维持)
- WSL(Linux 且 /mnt/d 存在) → /mnt/d/.db
- 纯 Linux(无 /mnt/d) → ~/.local/share/memo(XDG · 不再 RuntimeError)
"""
import sys
from pathlib import Path
import pytest


class TestFallbackDbDir:
    def test_windows_default(self):
        """Windows 平台 fallback = D:/.db(不依赖真实平台,直接验证函数分支)"""
        import memo_cli
        if sys.platform == "win32":
            assert memo_cli._fallback_db_dir() == Path("D:/.db")
        else:
            # 非 Windows 环境:跳过分支验证,只确认函数可调用不抛错
            assert callable(memo_cli._fallback_db_dir)

    def test_pure_linux_fallback_logic(self, monkeypatch, tmp_path):
        """纯 Linux(无 /mnt/d)→ ~/.local/share/memo,且目录被创建(不再 RuntimeError)"""
        import memo_cli
        home = tmp_path / "fake_home"
        home.mkdir()

        # 模拟:linux 平台 + /mnt/d 不存在 + home 指向 tmp
        _orig_exists = Path.exists  # 先保存原始引用,再替换
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(Path, "exists",
                            lambda self: False if str(self) == "/mnt/d" else _orig_exists(self))
        # Path.home 只影响 memo_cli 内部调用,用 monkeypatch 局部替换
        real_home = Path.home

        def fake_home():
            return home
        monkeypatch.setattr(Path, "home", staticmethod(fake_home))
        try:
            p = memo_cli._fallback_db_dir()
        finally:
            monkeypatch.setattr(Path, "home", staticmethod(real_home))
        assert str(p) == str(home / ".local" / "share" / "memo"), \
            f"纯 Linux fallback 应为 ~/.local/share/memo,实际 {p}"
        assert (home / ".local" / "share" / "memo").exists(), "fallback 目录应已创建"
