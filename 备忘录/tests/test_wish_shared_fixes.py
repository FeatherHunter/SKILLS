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

    def test_each_has_fallback_copy(self):
        """三模板都必须有 fallbackCopy 函数(或 execCommand fallback)· v1.1.5 共享化"""
        for name in self.EXPECTED_FILES:
            text = _read(name)
            # v1.1.5:共享 clipboard helper · 模板占位符由 injector 注入
            assert ("<!--INJECT-SHARED-->" in text), (
                f"{name} 必须有 <!--INJECT-SHARED--> 占位符 · "
                f"fallbackCopy 由 injector.py 注入(共享脚本 _shared/clipboard.js)"
            )

    def test_each_has_clearTimeout_in_btn_race(self):
        """btn 文字 setTimeout 必须配 clearTimeout 防止 race"""
        # 原 bug:连续采纳两次,第二次的文字 timer 还原会覆盖第一次的新文字
        for name in self.EXPECTED_FILES:
            text = _read(name)
            # 如果有 setTimeout(,必须有 clearTimeout(
            set_count = text.count("setTimeout(")
            if set_count == 0:
                continue
            clear_count = text.count("clearTimeout(")
            assert clear_count >= 1, (
                f"{name} 有 setTimeout 但没 clearTimeout — btn 文字 timer race"
            )


# ============================================================
# 采纳按钮 sticky
# ============================================================

class TestWishAdoptSticky:
    EXPECTED_FILES = ["wish_plan.html", "wish_complete.html", "change_category.html"]

    def test_each_has_adopt_button_with_position_fixed(self):
        """三模板的 .primary 按钮(采纳)必须有 position:fixed"""
        for name in self.EXPECTED_FILES:
            text = _read(name)
            # button.primary CSS 必须 fixed
            # 形态:.primary{...position:fixed}
            import re
            m = re.search(r"button\.primary\s*\{[^}]*\}", text)
            assert m, f"{name} button.primary CSS 块必须存在"
            css = m.group(0)
            assert ("position:fixed" in css
                    or "position: sticky" in css), (
                f"{name} button.primary 必须 position:fixed/sticky · "
                f"原 CSS:{css}"
            )

    def test_each_adopt_button_has_handler(self):
        """采纳按钮必须接 click handler(adopt() 或 addEventListener)"""
        for name in self.EXPECTED_FILES:
            text = _read(name)
            # button.primary onclick=adopt()
            import re
            m = re.search(r'<button[^>]*class="[^"]*primary[^"]*"[^>]*>', text)
            assert m, f"{name} <button class=primary> 节点必须存在"
            button_html = m.group(0)
            has_handler = ("onclick" in button_html
                           or re.search(r"\.primary[^}]*onclick|addEventListener\('click'[^)]*\.primary", text))
            assert has_handler, (
                f"{name} 采纳按钮必须有 click handler · 实际:{button_html}"
            )
