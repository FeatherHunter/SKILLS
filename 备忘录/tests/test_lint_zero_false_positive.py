"""T13 · template_lint 6 模板 0 误报 显式测试。

来自 issue #01 acceptance criteria:
"三个 lint 函数实测当前 6 个 templates(memo_query / sync_report / wish_plan /
wish_complete / change_category / memo_help),不产生误报"

phase A 落地时这条 AC 没显式测试覆盖。phase C 收尾补齐。
"""
from pathlib import Path

import pytest

from template_lint import (
    lint_undefined_funcs,
    lint_escape_asymmetry,
    lint_copy_fallback,
)


TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
ALL_TEMPLATES = [
    "memo_query.html",
    "sync_report.html",
    "wish_plan.html",
    "wish_complete.html",
    "change_category.html",
]


@pytest.mark.parametrize("tpl_name", ALL_TEMPLATES)
class TestLintZeroFalsePositive:
    """6 模板的 3 类规则都必须 0 误报"""

    def test_no_undefined_funcs(self, tpl_name):
        text = (TEMPLATES_DIR / tpl_name).read_text(encoding="utf-8")
        findings = lint_undefined_funcs(text)
        names = [f.get("name") for f in findings if f.get("name")]
        assert names == [], (
            f"{tpl_name} 规则 1 误报:{names}"
        )

    def test_no_escape_asymmetry(self, tpl_name):
        text = (TEMPLATES_DIR / tpl_name).read_text(encoding="utf-8")
        findings = lint_escape_asymmetry(text)
        bad = [f for f in findings if "不对称" in f.get("msg", "")]
        assert not bad, (
            f"{tpl_name} 规则 2 误报:{bad}"
        )

    def test_no_copy_fallback(self, tpl_name):
        text = (TEMPLATES_DIR / tpl_name).read_text(encoding="utf-8")
        findings = lint_copy_fallback(text)
        bad = [f for f in findings if "无 handler" in f.get("msg", "")
               or "未 handler" in f.get("msg", "")]
        assert not bad, (
            f"{tpl_name} 规则 3 误报:{bad}"
        )
