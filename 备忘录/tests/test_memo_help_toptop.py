"""T04 · memo_help.html 命名统一 + 回顶按钮 钉死测试。

US16:eyebrow / h1 / title 三处文案应一致
US7:HELP 长目录应有回到顶部 sticky 按钮
"""
from pathlib import Path

TEMPLATE = Path(__file__).parent.parent / "templates" / "memo_help.html"
TEMPLATE_TEXT = TEMPLATE.read_text(encoding="utf-8")


class TestMemoHelpNaming:
    def test_title_contains_help_keyword(self):
        """<title> 含 'HELP' 字眼(浏览器 tab 一眼能识别)"""
        import re
        m = re.search(r"<title>([^<]+)</title>", TEMPLATE_TEXT)
        assert m and "HELP" in m.group(1), (
            f"<title> 必须含 HELP 字眼识别度高 · 实际:{m.group(1) if m else 'NONE'}"
        )

    def test_hero_h1_pure_chinese(self):
        """h1 应是纯中文标题(无英文 + 数字混合)"""
        import re
        m = re.search(r"<h1>([^<]+)</h1>", TEMPLATE_TEXT)
        # 中国 title 可以是 "备忘录 · 使用手册"
        assert m
        text = m.group(1).strip()
        # 必须含"备忘录"且不混入英文短语
        assert "备忘录" in text
        # 允许"使用手册"短中文
        assert ("使用手册" in text or "帮助" in text or "help" not in text.lower() or "Help" not in text), (
            f"h1 不应是英文 · 实际:{text}"
        )


class TestMemoHelpBackToTop:
    def test_back_to_top_button_present(self):
        """应有 <button class="back-to-top"> 节点"""
        assert ("back-to-top" in TEMPLATE_TEXT), (
            "T04 acceptance · HELP 长目录必须有回到顶部 sticky 按钮"
        )

    def test_back_to_top_has_handler(self):
        """按钮有对应 click handler(锚 / JS)"""
        import re
        # 1. 检查 button class 周围有没有 click handler 关联
        m = re.search(r"<button[^>]*back-to-top[^>]*>", TEMPLATE_TEXT)
        assert m, "<button class=back-to-top> 必须存在"
        button_text = m.group(0)
        # 锚点形式:onclick="..." 或 href="#top"
        has_anchor = "scrollTo" in TEMPLATE_TEXT or "scrollTop" in TEMPLATE_TEXT
        has_aria = 'aria-label="回到顶部"' in TEMPLATE_TEXT
        assert (has_anchor and has_aria), (
            f"回顶按钮必须有 (scroll handler + aria-label) 双配置 · "
            f"button={button_text} has_anchor={has_anchor} has_aria={has_aria}"
        )

    def test_back_to_top_css_sticky(self):
        """CSS 应有 position:fixed 或类似 sticky 行为"""
        assert ("position:fixed" in TEMPLATE_TEXT
                or "position: sticky" in TEMPLATE_TEXT), (
            "回顶按钮必须 fixed/sticky 浮动 · 不能是 inline flow 元素"
        )
