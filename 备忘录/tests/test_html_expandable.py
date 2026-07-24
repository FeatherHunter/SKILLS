"""v1.0.8 可展开详情守护

扫描 SKILL.md 和 备忘录.html,确保每个触发词段都有 <details> 折叠区。
"""
import re
from pathlib import Path
import pytest

SKILL_DIR = Path(__file__).parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
MEMO_HTML = SKILL_DIR / "备忘录.html"

# 14 个应有 details 的触发词(去重 + 按段)
EXPECTED_DETAIL_SEGMENTS = [
    "添加笔记",          # 记备忘
    "搜索笔记",          # 搜备忘/查备忘
    "更新笔记",          # 改备忘
    "删除笔记",          # 删备忘
    "查看笔记详情",      # 看备忘
    "按时间搜索",        # 按时间搜备忘
    "编辑笔记顶层分类",  # 备忘改分类
    "编辑笔记子分类",    # 备忘改子分类
    "心愿排期",  # 心愿排期
    "设置提醒",          # 设提醒
    "记提醒(添笔记 + 设提醒)",  # 记提醒
    "查看提醒",          # 看提醒
    "查询已完成提醒",    # 查已提醒备忘
    "备忘录同步(自动 + 反向)",  # 备忘录同步
    "完成心愿:流式工作流",  # 完成心愿
]


class TestSkillMdExpandableDetails:
    """SKILL.md 每个触发词段下有 <details> 折叠区"""

    @pytest.fixture
    def text(self):
        return SKILL_MD.read_text(encoding="utf-8")

    @pytest.mark.parametrize("segment", EXPECTED_DETAIL_SEGMENTS)
    def test_segment_has_details(self, text, segment):
        """每个 ### 段(包含触发词)下应有 <details>"""
        # 找 ### 段位置
        pattern = r'### ' + re.escape(segment) + r'.*?(?=\n### |\n## )'
        m = re.search(pattern, text, re.DOTALL)
        assert m, f"找不到 ### {segment} 段"
        section = m.group(0)
        assert '<details>' in section, f"### {segment} 段缺 <details> 折叠区"

    def test_total_details_count(self, text):
        """至少 N 个 details(N = 14 触发词 + 1 子唤醒词 = 15)"""
        count = text.count('<details>')
        # 减去 2 个 placeholder("查看底层原理" 示例)
        assert count >= 15, f"details 数量 {count} 应 ≥ 15"


class TestMemoHtmlExpandableDetails:
    """备忘录.html 镜像每个触发词段下有 <details> 折叠区"""

    @pytest.fixture
    def text(self):
        return MEMO_HTML.read_text(encoding="utf-8")

    @pytest.mark.parametrize("segment", EXPECTED_DETAIL_SEGMENTS)
    def test_segment_has_details(self, text, segment):
        """每个 <h3> 或 <h4> 段下应有 <details>"""
        # 找 h3/h4 段(简化 regex:从 h 标签开始到下一个 h/hr)
        pattern = r'<h[34][^>]*>[^<]*' + re.escape(segment) + r'.*?(?=<h[1-6]|<hr)'
        m = re.search(pattern, text, re.DOTALL)
        assert m, f"找不到 <h3/h4>{segment}</h3/h4> 段"
        section = m.group(0)
        assert '<details>' in section, f"{segment} 段缺 <details> 折叠区"

    def test_total_details_count(self, text):
        """至少 N 个 details"""
        count = text.count('<details>')
        assert count >= 13, f"备忘录.html details 数量 {count} 应 ≥ 13"


class TestDesignPrincipleDoc:
    """SKILL.md 必须明确写"HTML 镜像设计原则"段"""

    def test_principle_section_exists(self):
        text = SKILL_MD.read_text(encoding="utf-8")
        assert "## HTML 镜像设计原则" in text, "SKILL.md 缺 'HTML 镜像设计原则' 段"

    def test_principle_explains_purpose(self):
        text = SKILL_MD.read_text(encoding="utf-8")
        section = re.search(
            r"## HTML 镜像设计原则.*?(?=\n## )",
            text, re.DOTALL,
        )
        assert section
        content = section.group(0)
        # 关键:HTML 是用户手册 + 可展开底层原理(不是日志)
        assert "用户手册" in content or "用户" in content
        assert "可展开" in content or "details" in content.lower()
        # CHANGELOG.md 才是日志
        assert "CHANGELOG" in content
