"""T05 · wish_plan / wish_complete / change_category 共享修复 钉死。

- 复制路径必须有 execCommand fallback(防 webview 拒绝)
- 采纳按钮必须 sticky fixed bottom(让用户不滚到 fold 之外也能采纳)
- btn 文字 timer 必须 clearTimeout 防 race(原 wish 模板有 race)
"""
from pathlib import Path

TEMPLATES = Path(__file__).parent.parent / "templates"


def _read(name):
    return (TEMPLATES / name).read_text(encoding="utf-8")


# ============================================================
# 复制路径 fallback
# ============================================================

class TestWishCopyFallback:
    EXPECTED_FILES = ["wish_plan.html", "wish_complete.html", "change_category.html"]

    def test_each_uses_base_copytext(self):
        """#299:三模板复制全走 Base copyText(SHARED-HELPERS 注入,含 execCommand fallback)"""
        for name in self.EXPECTED_FILES:
            text = _read(name)
            assert "<!--SHARED-HELPERS-->" in text, (
                f"{name} 必须有 SHARED-HELPERS 占位符 · copyText 由 Base base.js 注入"
            )
            assert "window.copyText" in text, (
                f"{name} 复制必须调 Base window.copyText"
            )
            assert "safeWriteText" not in text, (
                f"{name} 残留自研 safeWriteText(Base copyText 已含 fallback)"
            )

    def test_each_has_clearTimeout_in_btn_race(self):
        """btn 文字 setTimeout 必须配 clearTimeout 防止 race"""
        for name in self.EXPECTED_FILES:
            text = _read(name)
            set_count = text.count("setTimeout(")
            if set_count == 0:
                continue
            clear_count = text.count("clearTimeout(")
            assert clear_count >= 1, (
                f"{name} 有 setTimeout 但没 clearTimeout — btn 文字 timer race"
            )


# ============================================================
# 采纳按钮(设计变更:悬浮 → 面板内嵌)
# ============================================================

class TestWishAdoptSticky:
    EXPECTED_FILES = ["wish_plan.html", "wish_complete.html", "change_category.html"]

    def test_primary_button_not_floating(self):
        """#299 用户验收反馈:悬浮贴屏按钮删除,主按钮内嵌在指令面板里"""
        for name in self.EXPECTED_FILES:
            text = _read(name)
            import re
            m = re.search(r"button\.primary\s*\{[^}]*\}", text)
            assert m, f"{name} button.primary CSS 块必须存在"
            css = m.group(0)
            assert "position:fixed" not in css, (
                f"{name} 悬浮按钮应已删除(视觉审查:悬浮丑)· CSS:{css}"
            )

    def test_each_adopt_button_has_handler(self):
        """主按钮必须接 click handler(adopt())"""
        for name in self.EXPECTED_FILES:
            text = _read(name)
            import re
            m = re.search(r'<button[^>]*class="[^"]*primary[^"]*"[^>]*>', text)
            assert m, f"{name} <button class=primary> 节点必须存在"
            button_html = m.group(0)
            has_handler = ("onclick" in button_html)
            assert has_handler, (
                f"{name} 主按钮必须有 click handler · 实际:{button_html}"
            )
