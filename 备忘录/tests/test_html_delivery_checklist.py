"""v1.1.2 HTML 交付 checklist 守护

测试 SKILL.md "HTML 交付 checklist" 段必须含:
- checkbox 格式(`- [ ]`)而非 prose
- AGENT 回复模板(必须含"文件路径"+ "主动发送到了")
- 反例(不合格的表达)
"""
import re
from pathlib import Path
import pytest

SKILL_DIR = Path(__file__).parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"


class TestChecklistFormat:
    """v1.1.2:checklist 段必须用 checkbox 格式"""

    @pytest.fixture
    def section(self):
        text = SKILL_MD.read_text(encoding="utf-8")
        # 找"⚠️ HTML 交付 checklist" 段
        m = re.search(r"⚠️ HTML 交付 checklist.*?(?=\n## |\Z)", text, re.DOTALL)
        assert m, "SKILL.md 缺 '⚠️ HTML 交付 checklist' 段(v1.1.2 加)"
        return m.group(0)

    def test_has_checkbox_format(self, section):
        """必须含 ` - [ ] ` checkbox 格式(不是 prose)"""
        checkbox_count = len(re.findall(r'-\s*\[\s*\]', section))
        assert checkbox_count >= 3, \
            f"HTML 交付 checklist 段应含 ≥3 个 checkbox,实际 {checkbox_count}"

    def test_includes_path_generation_check(self, section):
        """checklist 含 'HTML 文件路径已生成' 检查"""
        assert "HTML 文件路径已生成" in section, \
            "checklist 缺 'HTML 文件路径已生成' 项"

    def test_includes_active_send_check(self, section):
        """checklist 含 '我用什么消息工具主动发送' 检查"""
        assert "我用什么消息工具主动发送" in section, \
            "checklist 缺 '主动发送'检查项(v1.1.1 核心诉求)"

    def test_includes_receiveable_check(self, section):
        """checklist 含 '用户能在他的设备上收到' 检查"""
        assert "用户能在" in section, \
            "checklist 缺'用户能收到'检查项"

    def test_includes_only_path_warning(self, section):
        """checklist 含'没有只输出路径就结束' 反例警告"""
        assert "只输出路径" in section or '只输出' in section, \
            "checklist 缺'我没只输出路径就结束吧' 反例警告"


class TestReplyTemplate:
    """v1.1.2:AGENT 回复模板(必须含主动发送路径)"""

    @pytest.fixture
    def section(self):
        text = SKILL_MD.read_text(encoding="utf-8")
        m = re.search(r"⚠️ HTML 交付 checklist.*?(?=\n## |\Z)", text, re.DOTALL)
        return m.group(0)

    def test_includes_reply_template(self, section):
        """含 AGENT 回复模板片段"""
        assert "回复模板" in section, \
            "checklist 段缺 '回复模板' 段"

    def test_template_mentions_file_path(self, section):
        """模板含 '文件路径:' """
        assert "文件路径" in section, \
            "AGENT 回复模板应含 '文件路径: <HTML 路径>'"

    def test_template_mentions_active_send(self, section):
        """模板含 '我主动发送到了'"""
        assert "主动发送" in section, \
            "AGENT 回复模板应含 '我主动发送到了'"

    def test_template_mentions_message_tool_examples(self, section):
        """模板给消息工具示例(飞书/微信/QQ 等)"""
        tools_examples = ["QQ", "微信", "飞书", "邮件"]
        mentioned = [t for t in tools_examples if t in section]
        assert len(mentioned) >= 3, \
            f"AGENT 回复模板应示例 ≥3 个消息工具,实际 {mentioned}"


class TestAntiExamples:
    """v1.1.2:反例段(不合格表达)"""

    @pytest.fixture
    def section(self):
        text = SKILL_MD.read_text(encoding="utf-8")
        m = re.search(r"⚠️ HTML 交付 checklist.*?(?=\n## |\Z)", text, re.DOTALL)
        return m.group(0)

    def test_has_anti_example_section(self, section):
        """含 '反例' 段"""
        assert "反例" in section, \
            "checklist 缺 '反例(以下都是不合格)' 段"

    def test_anti_examples_for_three_failures(self, section):
        """反例段 ≥3 个 ❌ 失败表达"""
        # 数 ❌ 标记
        fail_marks = section.count("❌")
        assert fail_marks >= 3, \
            f"反例段应有 ≥3 个 ❌ 标记(常见失败模式),实际 {fail_marks}"

    def test_anti_only_path_example(self, section):
        """反例之一:'只输出路径'"""
        assert "只输出路径" in section, \
            "反例应含 'HTML 已生成在 /path/...'(只给路径没主动发送)"


class TestSelfCheckTrigger:
    """v1.1.2:任务结束前的强制自检触发"""

    def test_section_says_must_walk_checklist(self):
        """checklist 段必须强调'必走一遍'"""
        text = SKILL_MD.read_text(encoding="utf-8")
        m = re.search(r"⚠️ HTML 交付 checklist.*?(?=\n## |\Z)", text, re.DOTALL)
        assert m
        section = m.group(0)
        assert "必走一遍" in section or "必走" in section, \
            "checklist 必须强调'任务结束前必走一遍'(防止 AGENT 跳过)"
