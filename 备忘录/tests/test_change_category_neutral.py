"""T08 · change_category.html .from 中性化 钉死。

原:.from{background:var(--err-soft);color:var(--err)} · 红色暗示"危险"
  但分类之间没有道德对错 · 红色 = 情绪化
新:.from{background:var(--bg);color:var(--fg2);border:1px solid var(--line)}
  中性灰 + 1px border · 只是状态标记
"""
from pathlib import Path

TEMPLATE = Path(__file__).parent.parent / "templates" / "change_category.html"
TEMPLATE_TEXT = TEMPLATE.read_text(encoding="utf-8")


class TestChangeCategoryNeutral:
    def test_from_no_err_color(self):
        """.from CSS 不再含 var(--err-soft) 或 var(--err)"""
        import re
        m = re.search(r"\.flow\s+\.from\s*\{[^}]*\}", TEMPLATE_TEXT)
        assert m, ".flow .from CSS 块必须存在"
        css = m.group(0)
        assert ("var(--err-soft)" not in css
                and "var(--err)" not in css), (
            f".from 不应用 err 色相(情绪化),实际:{css}"
        )

    def test_to_no_err_color_either(self):
        """.to CSS 也不应用 err 色相(对称约束)"""
        import re
        m = re.search(r"\.flow\s+\.to\s*\{[^}]*\}", TEMPLATE_TEXT)
        if m:
            css = m.group(0)
            assert ("var(--err-soft)" not in css
                    and "var(--err)" not in css), (
                f".to 不应用 err 色相,实际:{css}"
            )

    def test_from_has_neutral_border(self):
        """.from 应有 1px solid var(--line) border 视觉标记"""
        import re
        m = re.search(r"\.flow\s+\.from\s*\{[^}]*\}", TEMPLATE_TEXT)
        css = m.group(0)
        assert "border:" in css and "var(--line)" in css, (
            f".from 必须有 border:1px solid var(--line) · 中性标记,实际:{css}"
        )
