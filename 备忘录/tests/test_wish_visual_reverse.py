"""T06 · wish_* checkbox 视觉反转 钉死。

grill R2 + US19:已勾选 = line-through(opacity .5 · 表示已纳入采纳)
              未勾选 = 正常(未纳入)

原:未勾选 = .off 视觉降级(line-through) · 反用户心智
新:已勾选 = .on 视觉降级(line-through)
"""
import re
from pathlib import Path

TEMPLATES = Path(__file__).parent.parent / "templates"


def _read(name):
    return (TEMPLATES / name).read_text(encoding="utf-8")


class TestWishVisualReverse:
    FILES = ["wish_plan.html", "wish_complete.html"]

    def test_each_template_has_on_class(self):
        """两模板 CSS 必有 .on 视觉态定义"""
        for name in self.FILES:
            text = _read(name)
            # .wish.on 或 .on .content 形式
            assert (".wish.on" in text or "classList.toggle('on'" in text), (
                f"{name} 必有 .wish.on 视觉态(已勾选 = line-through)"
            )

    def test_each_template_uses_classList_toggle_on_in_event(self):
        """JS event handler 必须用 'on' 切换视觉"""
        for name in self.FILES:
            text = _read(name)
            assert "classList.toggle('on'" in text, (
                f"{name} checkbox 切换必须 classList.toggle('on', checked)"
            )

    def test_css_on_line_through(self):
        """CSS .on 应该有 line-through(opacity:.5 也好)"""
        for name in self.FILES:
            text = _read(name)
            # 模式:.wish.on .content{text-decoration:line-through}
            on_block = re.search(r"\.wish\.on\s*\{[^}]+\}", text)
            assert on_block, f"{name} .wish.on CSS 块必须存在"
            # 视觉态必须有 text-decoration 或 opacity
            assert ("text-decoration" in on_block.group(0)
                    or "opacity" in on_block.group(0)), (
                f"{name} .wish.on 必须有视觉区分(text-decoration 或 opacity)"
            )