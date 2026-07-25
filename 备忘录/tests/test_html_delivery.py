"""v1.1.1 HTML 交付规范 · 主动发送守护

测试 SKILL.md "HTML 交付规范" 段必须含:
- "<media>" 标签交付
- "主动发送给用户" / "主动发送" 硬性规则
- "Chrome" 浏览器打开(加分项,不强制)
- 不依赖特定消息工具(不硬编码飞书/QQ/微信)

来源:用户反馈 "AGENT 用 Chrome 打开了,但没主动把 HTML 发送到飞书/QQ/微信"
"""
import re
from pathlib import Path
import pytest

SKILL_DIR = Path(__file__).parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"


class TestHtmlDeliverySection:
    """v1.1.1 HTML 交付规范段必须含强制主动发送规则"""

    @pytest.fixture
    def section(self):
        text = SKILL_MD.read_text(encoding="utf-8")
        m = re.search(r"## HTML 交付规范.*?(?=\n## |\Z)", text, re.DOTALL)
        assert m, f"SKILL.md 缺 '## HTML 交付规范' 段"
        return m.group(0)

    def test_section_has_media_tag_rule(self, section):
        """必须含 <media> 交付规定"""
        assert "<media" in section, "HTML 交付规范必须含 <media> 标签交付"
        assert "src=" in section, "<media src=...> 必须是实际交付路径"

    def test_section_has_mandatory_send_rule(self, section):
        """v1.1.1:必须含'主动发送'硬性规则"""
        assert "主动" in section, "HTML 交付规范必须含'主动'(关键字)"
        assert ("主动发送" in section or "主动把" in section), \
            "v1.1.1 必须含'主动发送'/'主动把 HTML 发送出去'硬性规则"

    def test_section_no_hardcoded_message_tool(self, section):
        """不能硬编码消息工具(用户用飞书/QQ/微信 都可能,AI 自己判断)"""
        # 允许提到这些工具名作为"用户可能用"的说明,但不能写成"必须用 XX"
        hardcoded = re.search(r"必须用\s*(飞书|QQ|微信|邮件)", section)
        assert not hardcoded, \
            f"HTML 交付规范硬编码了消息工具:{hardcoded.group() if hardcoded else ''};" \
            "应该让 AI 自己判断用户当前可用的工具"
        # 但允许提及它们作为示例
        assert ("飞书" in section or "QQ" in section or "微信" in section), \
            "应该在文档中提及这些常用消息工具作为示例"

    def test_section_has_chrome_rule(self, section):
        """必须含 Chrome 浏览器打开(加分项)"""
        assert "Chrome" in section or "浏览器" in section, \
            "HTML 交付规范应提及 Chrome/浏览器"

    def test_section_says_chrome_is_optional(self, section):
        """Chrome 是加分项,不强制(主动发送才是核心)"""
        # 找到含 Chrome/浏览器 的描述,确认是"加分项"而非"必须"
        # 简单检查: 含 "加" / "可用" / "可选" / "推荐" / "加分" 等描述
        optional_keywords = ["加分", "可选", "可用", "推荐", "第二", "同时", "并行"]
        has_optional = any(kw in section for kw in optional_keywords)
        assert has_optional, \
            "Chrome/浏览器应该是加分项,而不是强制——主动发送才是核心"

    def test_section_acknowledges_user_not_at_chrome(self, section):
        """v1.1.1 新强加:用户可能不在 Chrome 前"""
        markers = [
            "用户可能不在", "用户当前可用", "用户当前可用",
            "用户不在 Chrome 前面", "用户用飞书", "用户用 QQ", "用户用微信",
        ]
        assert any(m in section for m in markers), \
            "HTML 交付规范应明确:用户可能不在 Chrome 前(手机/微信/飞书/QQ)"


class TestDeliveryMandatoryVsOptional:
    """v1.1.1 关键: 区分'必须'(主动发送) vs '加分'(Chrome)"""

    @pytest.fixture
    def section(self):
        text = SKILL_MD.read_text(encoding="utf-8")
        m = re.search(r"## HTML 交付规范.*?(?=\n## |\Z)", text, re.DOTALL)
        return m.group(0)

    def test_media_or_send_marked_mandatory(self, section):
        """ <media> 或'主动发送' 必须有'必须'/'硬性规定'标识"""
        # 找含 <media> 或'主动发送' 的描述段
        # 验证这些段含'必须'/'主动'/'硬性规定' 等强标识
        must_keywords = ["必须", "硬性", "强制", "不可省略", "核心"]
        # 看"必须"出现的位置
        sentences = re.split(r'[。\n]', section)
        has_mandatory_on_send = False
        for s in sentences:
            if ("主动发送" in s or "主动把" in s or "<media" in s):
                if any(kw in s for kw in must_keywords):
                    has_mandatory_on_send = True
                    break
        assert has_mandatory_on_send, \
            "主动发送规则必须有'必须'/'核心'/'硬性'标识(让 AI 知道是必须的,不是可选的)"
