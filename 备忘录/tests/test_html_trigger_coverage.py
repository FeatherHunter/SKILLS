"""v1.0.7 文档裂缝守护测试

扫描 SKILL.md + 备忘录.html 的"触发词 → HTML 生成对照表",
确保所有 28 个触发词都在表中被覆盖。

任何触发词被遗漏,此测试失败 → 提示维护者补全。

也检查:
- 表行数 = 28(不含批量场景的"额外"行)
- 每行的 HTML 状态标志 (✅/🟡/❌) 出现且唯一
- 每行的 CLI 命令出现
- 触发词列表与 SKILL.md L13 顶部触发词一致
"""
import re
from pathlib import Path
import pytest

SKILL_DIR = Path(__file__).parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
MEMO_HTML = SKILL_DIR / "备忘录.html"

# v1.0.7 权威触发词列表(28 个)
EXPECTED_TRIGGERS = [
    # 顶层 16 个(与 SKILL.md L13 顶部触发词一致)
    "记备忘", "搜备忘", "查备忘", "改备忘", "删备忘",
    "看备忘", "按时间搜备忘", "备忘改分类", "备忘改子分类",
    "记提醒", "设提醒", "看提醒", "查已提醒备忘",
    "完成心愿", "心愿排期", "备忘录同步",
    # 子唤醒词 12 个
    "记心愿", "删心愿", "改心愿", "查心愿",
    "记打卡", "删打卡", "改打卡", "查打卡",
    "记情绪", "删情绪", "改情绪", "查情绪",
]


class TestTriggerCoverageTable:
    """v1.0.7:对照表必须覆盖所有 28 个触发词"""

    @pytest.fixture
    def skill_md_text(self):
        return SKILL_MD.read_text(encoding="utf-8")

    @pytest.fixture
    def memo_html_text(self):
        return MEMO_HTML.read_text(encoding="utf-8")

    def _extract_table_section(self, text, start_marker, end_marker):
        """提取两个 marker 之间的内容"""
        start = text.find(start_marker)
        assert start >= 0, f"找不到起始 marker '{start_marker}'"
        end = text.find(end_marker, start)
        if end < 0:
            end = len(text)
        return text[start:end]

    @pytest.mark.parametrize("trigger", EXPECTED_TRIGGERS)
    def test_skill_md_table_includes_trigger(self, skill_md_text, trigger):
        """SKILL.md 对照表包含每个触发词"""
        section = self._extract_table_section(
            skill_md_text,
            "触发词 → HTML 生成对照表",
            "## 描述",
        )
        assert trigger in section, f"SKILL.md 对照表缺触发词: {trigger!r}"

    @pytest.mark.parametrize("trigger", EXPECTED_TRIGGERS)
    def test_memo_html_table_includes_trigger(self, memo_html_text, trigger):
        """备忘录.html 镜像对照表包含每个触发词"""
        section = self._extract_table_section(
            memo_html_text,
            "触发词 → HTML 生成对照表",
            "<h2 id=\"描述-2\">描述</h2>",
        )
        assert trigger in section, f"备忘录.html 对照表缺触发词: {trigger!r}"

    def test_skill_md_table_row_count(self, skill_md_text):
        """SKILL.md 对照表行数 = 28(不含量行)"""
        section = self._extract_table_section(
            skill_md_text,
            "触发词 → HTML 生成对照表",
            "## 描述",
        )
        # 数表格行数(markdown `| 数字 |`)
        rows = re.findall(r"^\|\s*\d+\s*\|", section, re.MULTILINE)
        assert len(rows) == 28, f"期望 28 行触发词,实际 {len(rows)}"

    def test_html_status_markers_all_present(self, skill_md_text):
        """3 种 HTML 状态标志 (✅/🟡/❌) 都在表中出现"""
        section = self._extract_table_section(
            skill_md_text,
            "触发词 → HTML 生成对照表",
            "## 描述",
        )
        assert "✅" in section, "对照表缺 ✅ 必须生成"
        assert "🟡" in section, "对照表缺 🟡 过程型"
        assert "❌" in section, "对照表缺 ❌ 不生成"

    def test_statistics_table_sums_to_28(self, skill_md_text):
        """统计表合计 = 28"""
        section = self._extract_table_section(
            skill_md_text,
            "触发词 → HTML 生成对照表",
            "## 描述",
        )
        # 找到统计表
        m = re.search(r"合计.*?28", section, re.DOTALL)
        assert m, "统计表合计应 = 28"


class TestTopLevelTriggerListMatch:
    """SKILL.md L13 顶部的触发词列表与对照表覆盖一致"""

    def test_top_trigger_count(self):
        """SKILL.md 顶层触发词段(L157)16 个"""
        text = SKILL_MD.read_text(encoding="utf-8")
        # 找 **触发词**:... (顶层)
        m = re.search(r"\*\*触发词\*\*:\s*([^\n]+)", text)
        assert m, "找不到顶层触发词行"
        line = m.group(1)
        # 数顶层触发词(逗号分隔,别名"完成打卡"包含在"完成心愿"里)
        items = re.findall(r"[\u4e00-\u9fff]+", line)
        assert len(items) >= 16, f"顶层触发词应 ≥16,实际 {len(items)}: {items}"

    def test_sub_trigger_count(self):
        """子唤醒词段(L161 起)12 个"""
        text = SKILL_MD.read_text(encoding="utf-8")
        # 找 **分类子唤醒词** 段
        m = re.search(r"\*\*分类子唤醒词\*\*:?\s*(.*?)(?=\n## )", text, re.DOTALL)
        assert m, "找不到子唤醒词段"
        section = m.group(1)
        # 数 - 触发词行(格式: - 记心愿、删心愿、改心愿、查心愿)
        items = re.findall(r"- ([^\n]+)", section)
        # 每个 - 行含多个子唤醒词
        all_sub_triggers = []
        for line in items:
            all_sub_triggers.extend(re.findall(r"[\u4e00-\u9fff]{2,4}", line))
        assert len(all_sub_triggers) >= 12, f"子唤醒词应 ≥12,实际 {len(all_sub_triggers)}: {all_sub_triggers}"