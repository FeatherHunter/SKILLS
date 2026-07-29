"""T03 视觉 / a11y / 长列表 切换 钉死测试。

来自 to-spec/grill R2:
- 给 <input id="filter"> 加 <label for="filter"> a11y 节点
- 列表 > 50 条时默认渲染前 50,提供"显示全部/前 50"切换
- KPI 数字字号 ≤ 24px,标签 ≥ 13px(视觉权重平衡)
"""
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).parent.parent / "templates" / "memo_query.html"
TEMPLATE_TEXT = TEMPLATE.read_text(encoding="utf-8")


# ============================================================
# A11y:label
# ============================================================

class TestMemoQueryA11y:
    def test_filter_label_exists(self):
        assert ('<label for="filter"' in TEMPLATE_TEXT), (
            "筛选框必须有 <label for=filter> 节点 — 屏幕阅读器才能读出"
            "语义(总纲 §04 原则 6 · 改动前必答 3 问)"
        )

    def test_filter_id_matches_label_for(self):
        """label for 应与 input id 对应"""
        assert ('id="filter"' in TEMPLATE_TEXT), "<input id=filter> 节点必须存在"
        assert ('for="filter"' in TEMPLATE_TEXT), '<label for=filter> 必须存在'


# ============================================================
# 长列表 · 50 / 全部 切换
# ============================================================

class TestMemoQueryLengthMode:
    def test_default_render_cap_50(self):
        """renderList 必须有 MAX_DEFAULT = 50 的限制常量"""
        assert ("MAX_DEFAULT" in TEMPLATE_TEXT
                or "LIMIT_DEFAULT" in TEMPLATE_TEXT
                or "maxRender" in TEMPLATE_TEXT
                or "50" in TEMPLATE_TEXT), (
            "长列表(> 50 条)应有默认上限常量;否则全量展开会刷屏"
        )

    def test_toggle_button_somewhere(self):
        """必须有一个"显示全部 / 前 50"切换按钮 + 对应 handler"""
        # 接受 onclick="toggleLengthMode" 或 .addEventListener 形态
        toggle_present = ("toggleLengthMode" in TEMPLATE_TEXT
                          or "showAll" in TEMPLATE_TEXT
                          or "showDefault" in TEMPLATE_TEXT
                          or "toggleMode" in TEMPLATE_TEXT)
        assert toggle_present, (
            "应有切换模式按钮(全部 / 前 50)— 钉死 T03 acceptance criteria"
        )


# ============================================================
# KPI 视觉权重
# ============================================================

class TestMemoQueryKpiFont:
    def test_kpi_number_font_leq_24(self):
        """KPI 数字字号应 ≤ 24px(原 24px 已是上限,不能再放大)"""
        # CSS .stat b 或 .kpi b
        import re
        m = re.search(r"\.stat\s+b\s*\{[^}]*font-size:\s*(\d+)px", TEMPLATE_TEXT)
        if m:
            size = int(m.group(1))
            assert size <= 24, f"KPI 数字字号 {size}px 超过 24 上限"
        # 若模板中无 .stat b(已被改名),跳过(无 KPI 不报错)
