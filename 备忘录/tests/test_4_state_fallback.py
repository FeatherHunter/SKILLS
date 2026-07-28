"""v1.1.5 · 4 状态 fallback 守护(ticket 07 · B.9 决策)

4 状态:success / empty / missing_data / error
(原 5 状态含 offline,B.9 决策"不存在所谓离线的场景"已删)

每模板的 init() JS 必须显式含 success 路径标记(注释或函数调用),
让 fallback 状态可预测、可审计。
"""
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# 6 个模板(memo_help 是 HELP,其余 5 个是业务模板)
ALL_TEMPLATES = [
    "memo_help.html",
    "memo_query.html",
    "sync_report.html",
    "wish_plan.html",
    "wish_complete.html",
    "change_category.html",
]


class TestFourStateFallback:
    """B.9 决策:4 状态 fallback(success / empty / missing_data / error)。"""

    def test_no_offline_state_in_templates_or_scripts(self):
        """offline 状态已删(B.9 决策)—— templates/ + script/ 不得含 'offline' 字样。"""
        for tpl in ALL_TEMPLATES:
            text = (TEMPLATES_DIR / tpl).read_text(encoding="utf-8")
            assert "offline" not in text.lower(), f"{tpl} 含 'offline' 字样(应已删)"

    def test_each_template_has_explicit_success_marker(self):
        """每模板 init() 必须显式标记 success 路径(注释或 showState 调用)。"""
        for tpl in ALL_TEMPLATES:
            text = (TEMPLATES_DIR / tpl).read_text(encoding="utf-8")
            # 接受任一形式:showState('Success') / // success / state: success / class="success"
            markers = [
                "showState('Success')",
                'showState("Success")',
                "// success",
                "state: success",
                'class="success"',
                "stateSuccess",
            ]
            assert any(m in text for m in markers), (
                f"{tpl} 缺 success 状态标记(任一:{markers})"
            )

    def test_each_template_has_empty_state(self):
        """每模板必须有 empty 状态处理(无数据时的空态)。"""
        for tpl in ALL_TEMPLATES:
            text = (TEMPLATES_DIR / tpl).read_text(encoding="utf-8")
            assert "empty" in text.lower(), f"{tpl} 缺 empty 状态处理"

    def test_each_template_has_error_state(self):
        """每模板必须有 error 状态处理(异常时的错误态)。"""
        for tpl in ALL_TEMPLATES:
            text = (TEMPLATES_DIR / tpl).read_text(encoding="utf-8")
            # error 可能是 catch 块、showState('Error')、class="error" 等
            error_markers = ["error", "Error", "catch"]
            assert any(m in text for m in error_markers), f"{tpl} 缺 error 状态处理"

    def test_help_template_has_4_state_banners(self):
        """memo_help.html 是状态最全的模板,必须有 4 个 state banner(success/empty/missing/error)。"""
        text = (TEMPLATES_DIR / "memo_help.html").read_text(encoding="utf-8")
        for state_id in ["stateSuccess", "stateEmpty", "stateMissing", "stateError"]:
            assert state_id in text, f"memo_help.html 缺 4 状态 banner: {state_id}"
