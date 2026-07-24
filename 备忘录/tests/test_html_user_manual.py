"""v1.0.9 纯用户手册守护

验证 备忘录.html:
1. 是用户手册(唤醒词 + 用法 + <details> 展开)
2. 不含"日志/改动/AI 规则"性质的内容:
   - 顶部版本号
   - 历史版本列表
   - "强制性规定"
   - "HTML 交付规范"
   - "触发词 → HTML 生成对照表"
   - "AGENT 决策流程"
   - "Cron / 提醒逻辑"(内部机制)
3. 28 个触发词都覆盖
4. 每个触发词段有 <details> 折叠区(让用户看底层)
"""
import re
from pathlib import Path
import pytest

MEMO_HTML = Path(__file__).parent.parent / "备忘录.html"


class TestUserManualDesign:
    """v1.0.9 备忘录.html = 纯用户手册"""

    @pytest.fixture
    def text(self):
        return MEMO_HTML.read_text(encoding="utf-8")

    # ---- 不应包含的(日志/改动/AI 规则)----

    def test_no_version_history(self, text):
        """不应有版本号 + 历史版本列表(那是 CHANGELOG.md 的事)"""
        assert "当前版本:" not in text, "顶部不应有'当前版本: vX.Y.Z'(那是日志)"
        # 不应有"v1.0.x 发布"的多行历史
        assert text.count("发布") < 3, f"过多'发布'字样,疑似版本历史(应 < 3,实际 {text.count('发布')})"

    def test_no_mandatory_rules(self, text):
        """不应有'强制性规定'段(给 AI 看的)"""
        assert "强制性规定" not in text, "不应有'强制性规定'段(给 AI 看的)"

    def test_no_html_delivery_spec(self, text):
        """不应有'HTTP 交付规范'段(给 AI 决策用)"""
        assert "HTML 交付规范" not in text, "不应有'HTML 交付规范'(给 AI 决策)"

    def test_no_trigger_html_mapping(self, text):
        """不应有'触发词 → HTML 生成对照表'段(给 AI 决策用)"""
        assert "触发词 → HTML 生成对照表" not in text, "不应有'HTML 对照表'(给 AI)"

    def test_no_agent_decision_flow(self, text):
        """不应有'AGENT 决策流程'(给 AI)"""
        assert "AGENT 决策流程" not in text, "不应有'AGENT 决策流程'(给 AI)"

    def test_no_internal_cron(self, text):
        """不应有'提醒逻辑'/'提醒输出格式'(内部机制)"""
        assert "提醒逻辑" not in text, "不应有'提醒逻辑'(内部机制)"
        # 允许 Cron 配置(用户配置用),但不允许 "提醒输出格式(SKILL 内部执行时使用)"

    def test_no_anti_doc_chaos(self, text):
        """不应有'防文档裂缝守护'"""
        assert "防文档裂缝守护" not in text, "不应有'防文档裂缝守护'(开发者关注)"

    def test_no_old_deprecated_flow(self, text):
        """不应有'完成提醒:提醒与打卡的完整流程(旧流程)'"""
        assert "完成提醒:提醒与打卡的完整流程" not in text, "不应有 deprecated 旧流程"

    # ---- 应该包含的(用户手册)----

    def test_has_intro_section(self, text):
        """应有'简介'/'是什么'说明"""
        assert "📝 备忘录" in text, "应有标题"
        assert "私人备忘工具" in text, "应有简介"

    def test_has_quick_start(self, text):
        assert "快速开始" in text

    def test_has_env_vars_table(self, text):
        assert "环境变量" in text
        assert "SKILLS_DB_PATH" in text
        assert "MEMO_MEDIA_DIR" in text

    def test_has_reminder_routing_warning(self, text):
        """重要约定:提醒路由(防用户用错工具)"""
        assert "提醒路由" in text
        assert "qqbot_remind" in text or "提醒工具" in text

    def test_has_trigger_speed_query(self, text):
        """触发词速查表(28 个)"""
        assert "触发词速查表" in text
        # 数 28 个 <span class="pill">
        pill_count = text.count('<span class="pill')
        assert pill_count >= 28, f"速查表应有 ≥ 28 pill,实际 {pill_count}"

    def test_has_all_28_triggers(self, text):
        """28 个触发词都覆盖"""
        triggers = [
            "记备忘", "搜备忘", "查备忘", "改备忘", "删备忘", "看备忘", "按时间搜备忘",
            "备忘改分类", "备忘改子分类", "记提醒", "设提醒", "看提醒", "查已提醒备忘",
            "完成心愿", "心愿排期", "备忘录同步",
            "记心愿", "删心愿", "改心愿", "查心愿",
            "记打卡", "删打卡", "改打卡", "查打卡",
            "记情绪", "查情绪",
        ]
        for t in triggers:
            assert t in text, f"触发词 '{t}' 不在用户手册中"

    def test_has_grouped_detail_sections(self, text):
        """触发词详细按"做什么"分组"""
        for group in ["记录类", "查找类", "提醒类", "心愿类", "批量类", "跨 Skill", "子唤醒词"]:
            assert group in text, f"缺分组 '{group}'"

    def test_has_sub_wake_words_section(self, text):
        """子唤醒词(12 个)有专门说明"""
        assert "子唤醒词" in text
        for sub in ["记心愿", "查心愿", "记打卡", "查打卡", "记情绪", "查情绪"]:
            assert sub in text

    def test_has_cron_section(self, text):
        """定时提醒(Cron)配置"""
        assert "Cron" in text or "cron" in text
        assert "reminder_scheduler" in text

    def test_has_details_for_user_expansion(self, text):
        """可展开 <details> 让用户看底层"""
        details_count = text.count("<details>")
        assert details_count >= 20, f"用户手册应有 ≥ 20 <details>(让用户点开看底层),实际 {details_count}"

    def test_has_footer_linking_to_changelog_and_skill(self, text):
        """footer 应有 CHANGELOG.md 和 SKILL.md 链接(让用户知道去哪看其他)"""
        assert "CHANGELOG.md" in text
        assert "SKILL.md" in text

    def test_user_manual_no_changelog_section_in_body(self, text):
        """不应在 body 里有 changelog 段(footer 链接 OK)"""
        # body 里不应有"## [v" / "## v" / "[Unreleased]" 段
        body_pattern = r'<h[12][^>]*>.*?(?:\[?\d+\.\d+\.\d+\]?|v\d+\.\d+\.\d+).*?</h[12]>'
        version_h_tags = re.findall(body_pattern, text, re.DOTALL)
        assert not version_h_tags, f"body 不应有版本号 h 标签,实际: {version_h_tags}"


class TestUserManualReadability:
    """可读性 / UX"""

    @pytest.fixture
    def text(self):
        return MEMO_HTML.read_text(encoding="utf-8")

    def test_has_toc(self, text):
        """有目录"""
        assert "目录" in text or "TOC" in text

    def test_has_mobile_responsive(self, text):
        """移动端适配"""
        assert "@media" in text
        assert "max-width:600px" in text or "max-width: 600px" in text

    def test_no_unclosed_tags(self, text):
        """基本 HTML 标签平衡(用 regex 数 <tag...> 形式,支持 id)"""
        import re
        # <details> 平衡
        open_details = len(re.findall(r'<details(?:\s[^>]*)?>', text))
        close_details = text.count("</details>")
        assert open_details == close_details, (
            f"<details> {open_details} 个,</details> {close_details} 个,不匹配"
        )
        # <summary> 平衡
        assert text.count("<summary>") == text.count("</summary>")
        # <h2>/<h4> 平衡(可能带 id 属性)
        for tag in ["h2", "h4"]:
            opens = len(re.findall(rf'<{tag}(?:\s[^>]*)?>', text))
            closes = text.count(f"</{tag}>")
            assert opens == closes, f"<{tag}> {opens} 个,</{tag}> {closes} 个,不匹配"
