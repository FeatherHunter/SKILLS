"""v1.1.4 · HELP HTML 可读性守护

取代 v1.0.9 的"纯用户手册守护":现在 备忘录.html 是自动生成的 HELP 页,
不再是手写版。检查新 HELP HTML 的可读性 / UX 关键点。

总纲 §07 §5:适配手机 + PC,失败/空数据不静默,支持大规模场景折叠。
"""
import re
from pathlib import Path
import pytest

MEMO_HTML = Path(__file__).parent.parent / "备忘录.html"


class TestHelpHtmlReadability:
    @pytest.fixture
    def text(self):
        return MEMO_HTML.read_text(encoding="utf-8")

    def test_has_toc(self, text):
        """目录锚点(总纲 §04 原则 3)"""
        assert "toc" in text, "应有目录 toc"

    def test_has_mobile_responsive(self, text):
        """移动端适配(总纲 §07 §5)"""
        assert "@media" in text, "缺 @media 移动适配"
        assert "max-width" in text, "缺响应式断点"

    def test_has_search_filter(self, text):
        """总纲 §07 §5:大规模场景可搜索/筛选"""
        assert "filter" in text or "search" in text.lower(), \
            "缺搜索/筛选"

    def test_has_5_state_fallback(self, text):
        """总纲 §04 原则 3:5 状态 fallback"""
        for state_id in ["stateEmpty", "stateMissing", "stateError"]:
            assert state_id in text, f"缺 5 状态 banner: {state_id}"

    def test_has_copy_button(self, text):
        """总纲 §07 §5:每场景独立复制按钮"""
        assert "copyPrompt" in text or "复制 prompt" in text, \
            "缺复制按钮机制"

    def test_has_clipboard_fallback(self, text):
        """总纲 §07 §5:剪贴板 API 不可用时降级"""
        assert "fallbackCopy" in text or "execCommand" in text, \
            "缺剪贴板降级"

    def test_has_escape_html(self, text):
        """总纲 §04 原则 4:XSS 防护"""
        assert "escapeHTML" in text or "esc(" in text, \
            "缺 XSS 转义函数"

    def test_no_unclosed_tags(self, text):
        """基本 HTML 标签平衡"""
        # <details> 平衡
        open_details = len(re.findall(r'<details(?:\s[^>]*)?>', text))
        close_details = text.count("</details>")
        assert open_details == close_details, \
            f"<details> {open_details} 个,</details> {close_details} 个,不匹配"
        # <summary> 平衡
        assert text.count("<summary>") == text.count("</summary>")

    def test_placeholder_unique(self, text):
        """总纲 §04 原则 4:占位符唯一"""
        count = text.count("<!--INJECT-DATA-->")
        assert count == 1, f"占位符 <!--INJECT-DATA--> 应为 1 个,实际 {count}"


class TestHelpHtmlStructure:
    """总纲 §07 §5:HELP HTML 必须含全部业务唤醒词 + 全部合法场景"""

    @pytest.fixture
    def text(self):
        return MEMO_HTML.read_text(encoding="utf-8")

    def test_has_28_business_wake_words(self, text):
        """§07 §5:展示全部业务唤醒词"""
        expected = [
            "记备忘", "搜备忘", "查备忘", "改备忘", "删备忘", "看备忘",
            "按时间搜备忘", "备忘改分类", "备忘改子分类",
            "记提醒", "设提醒", "看提醒", "查已提醒备忘",
            "记心愿", "删心愿", "改心愿", "查心愿",
            "记打卡", "删打卡", "改打卡", "查打卡",
            "记情绪", "删情绪", "改情绪", "查情绪",
            "完成心愿", "心愿排期", "备忘录同步",
        ]
        for t in expected:
            assert t in text, f"HELP HTML 缺唤醒词: {t}"

    def test_has_7_groups(self, text):
        """§04 原则 3:按维度分组(场景按类别分组)"""
        for g in ["记录类", "查找类", "提醒类", "心愿类", "批量类", "跨 Skill", "子唤醒词"]:
            assert g in text, f"缺分组: {g}"

    def test_help_not_show_itself(self, text):
        """§07 §5 反模式 3:HELP 唤醒词自身不出现在 HTML"""
        # 不应在分组里出现 "HELP" 触发词
        # 但场景数据里的 prompt/result 可以提到"看 help"等
        # 关键检查:scenario_id 不应是 memo_help 自身
        assert "scenario_id: memo_help" not in text, \
            "HELP HTML 不应展示 HELP 自身的场景"

    def test_no_cli_or_db_leak_in_html(self, text):
        """§07 §3 反例:HTML 也不暴露 CLI / DB(用户从 HTML 复制 prompt 给 AI,prompt 应抽象)"""
        forbidden = ["memo_cli.py", "memo.db", "templates/", "script/"]
        leaks = [f for f in forbidden if f in text]
        assert not leaks, f"HTML 暴露实现细节: {leaks}"