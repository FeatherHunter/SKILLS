"""4 状态 fallback 守护(#299 Base 重构后 · emptyState/errorReceipt 版)

4 状态:success / empty / missing_data / error
(原 5 状态含 offline,B.9 决策"不存在所谓离线的场景"已删)

#299 迁移:原「state-banner 横幅」→ Base emptyState(空态)/ errorReceipt(错态);
每模板必须调用这两控件,success 路径 = 正常渲染(无横幅)。
"""
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# 6 个业务模板(memo_help 已退役 · HELP 走 Base help_template)
ALL_TEMPLATES = [
    "memo_query.html",
    "sync_report.html",
    "wish_plan.html",
    "wish_complete.html",
    "change_category.html",
    "init_report.html",
]


class TestFourStateFallback:
    """4 状态 fallback(success / empty / missing_data / error) · Base 控件版。"""

    def test_no_offline_state_in_templates_or_scripts(self):
        """offline 状态已删(B.9 决策)—— templates/ 不得含 'offline' 字样。"""
        for tpl in ALL_TEMPLATES:
            text = (TEMPLATES_DIR / tpl).read_text(encoding="utf-8")
            assert "offline" not in text.lower(), f"{tpl} 含 'offline' 字样(应已删)"

    def test_each_template_has_explicit_success_marker(self):
        """每模板必须显式标记 success 路径(注释)。"""
        for tpl in ALL_TEMPLATES:
            text = (TEMPLATES_DIR / tpl).read_text(encoding="utf-8")
            markers = [
                "// success",
                "success: ",
                "stateSuccess",
            ]
            assert any(m in text for m in markers), (
                f"{tpl} 缺 success 状态标记(任一:{markers})"
            )

    def test_each_template_has_empty_state(self):
        """每模板必须有 empty 状态处理 → Base emptyState(#299 迁移)"""
        for tpl in ALL_TEMPLATES:
            text = (TEMPLATES_DIR / tpl).read_text(encoding="utf-8")
            assert "emptyState" in text, f"{tpl} 缺 emptyState 空态处理(#299 Base 控件)"

    def test_each_template_has_error_state(self):
        """每模板必须有 error 状态处理 → Base errorReceipt(#299 迁移)"""
        for tpl in ALL_TEMPLATES:
            text = (TEMPLATES_DIR / tpl).read_text(encoding="utf-8")
            assert "errorReceipt" in text, f"{tpl} 缺 errorReceipt 错误态处理(#299 Base 控件)"

    def test_help_uses_base_template(self):
        """HELP 已退役自研 memo_help.html · 渲染走 Base help_template(#299)"""
        assert not (TEMPLATES_DIR / "memo_help.html").exists(), \
            "自研 memo_help.html 应已退役(Base help_template 替代)"
        from memo_render import BASE_HELP_TEMPLATE_PATH
        assert BASE_HELP_TEMPLATE_PATH.name == "help_template.html"
        text = BASE_HELP_TEMPLATE_PATH.read_text(encoding="utf-8")
        assert "help-data" in text, "Base help_template 应有 help-data 注入点"
