"""#299 · 复制反馈 Toast 守护(Base toast 组件版)

原 memo_help.html 自研 toast(showToast/#toast)随 HELP 退役(#295 决策 9:
HELP 页接受 Base 内置标准文案)。本文件守护:
- render_help 产物含 Base toast 机制(base.js 注入:window.toast + .hm-toast + 知道了)
- 业务模板复制反馈 = 自定义 toast 文案(#295 文案表)
"""
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).parent.parent
BUSINESS_TEMPLATES = [
    "memo_query.html",
    "sync_report.html",
    "wish_plan.html",
    "wish_complete.html",
    "change_category.html",
    "init_report.html",
]


class TestCopyPromptToastFeedback:
    """Base toast 组件守护(渲染产物层面)"""

    @pytest.fixture(scope="class")
    def rendered_help(self):
        from memo_render import render_help
        return render_help()

    def test_help_has_base_toast(self, rendered_help):
        """Base toast:window.toast 定义 + 毛玻璃 CSS + ✓ 知道了 关闭按钮"""
        text = Path(rendered_help["skill_root_path"]).read_text(encoding="utf-8")
        assert "window.toast = function" in text, "缺 Base toast 定义"
        assert ".hm-toast" in text, "缺 Base toast CSS"
        assert "知道了" in text, "缺 toast 关闭按钮(✓ 知道了)"
        assert "setTimeout" in text, "缺 toast 自动消失"

    def test_help_has_base_copy_feedback(self):
        """HELP 复制反馈 = Base 内置标准文案(决策 9)"""
        from pathlib import Path as P
        from memo_render import render_help
        r = render_help()
        text = P(r["skill_root_path"]).read_text(encoding="utf-8")
        assert "已复制" in text and "粘贴给 AI" in text, "缺 Base 标准复制文案"

    def test_help_has_no_legacy_memo_toast(self):
        """旧 memo_help 专属 toast 元素已退役(Base 模板自有其内部结构)"""
        from pathlib import Path as P
        from memo_render import render_help
        r = render_help()
        text = P(r["skill_root_path"]).read_text(encoding="utf-8")
        assert "toastWake" not in text, "残留旧 memo_help 唤醒词 toast 结构"


class TestBusinessToastCopy:
    """业务页复制反馈 = 自定义 toast(#295 文案表 · 按钮文字恒定)"""

    @pytest.mark.parametrize("tpl", BUSINESS_TEMPLATES)
    def test_each_has_custom_toast(self, tpl):
        text = (SKILL_DIR / "templates" / tpl).read_text(encoding="utf-8")
        assert "window.toast(" in text, f"{tpl}: 复制反馈应走 Base toast"

    def test_button_text_constant_no_self_flash(self):
        """按钮文字恒定:无 flashBtn/✓ 已复制 按钮内嵌反馈(反馈只走 toast)"""
        for tpl in BUSINESS_TEMPLATES:
            text = (SKILL_DIR / "templates" / tpl).read_text(encoding="utf-8")
            assert "flashBtn" not in text, f"{tpl}: 残留 flashBtn 按钮文字反馈"
            assert "✓ 已复制" not in text, f"{tpl}: 残留按钮内嵌反馈(应走 toast)"

    def test_query_custom_toast_copy(self):
        """#295 文案表:memo_query 单条复制/筛选结果自定义文案"""
        text = (SKILL_DIR / "templates" / "memo_query.html").read_text(encoding="utf-8")
        assert "已复制这条备忘" in text, "缺单条复制自定义 toast"
        assert "筛选结果已复制" in text, "缺筛选结果自定义 toast"
        assert "复制失败" in text and "长按选择文本手动复制" in text, "缺失败 toast"

    def test_wizard_adopt_toast(self):
        """向导:指令已复制 toast(替代旧 alert/采纳成功)"""
        for tpl in ["wish_plan.html", "wish_complete.html", "change_category.html"]:
            text = (SKILL_DIR / "templates" / tpl).read_text(encoding="utf-8")
            assert "指令已复制" in text, f"{tpl}: 缺指令已复制 toast"
            assert "alert(" not in text, f"{tpl}: 残留 alert(应走 toast warn)"
