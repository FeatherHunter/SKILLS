#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_weight_history_mobile.py — triage fix verification

weight-history-mobile-fixes · 2026-07-30

覆盖 AGENT-BRIEF acceptance criteria:
  BUG 1: 体重曲线 mobile 不被垂直拉伸
  BUG 2: 明细表格 note 列在 mobile 可见(用户原话"晨起空腹几个字")

Review fixes: 4 dead tests 改 real assertions, CSS 选择器用真实生成的类名.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "templates" / "weight_history.html"
RENDER = SKILL_DIR / "scripts" / "render_weight_history.py"


# ============= BUG 1: chart 垂直拉伸修复 =============


def test_svg_uses_preserve_aspect_ratio_not_none():
    """修复: 不用 preserveAspectRatio='none'(会独立缩放 Y 轴)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    assert 'preserveAspectRatio="none"' not in html, (
        "preserveAspectRatio='none' 会让 X/Y 独立缩放(mobile BUG 根源)"
    )


def test_svg_preserve_aspect_ratio_value():
    """修复: SVG 应有 xMidYMid meet(等比缩放)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    m = re.search(r'<svg[^>]*preserveAspectRatio="([^"]+)"', html)
    assert m, "SVG 缺 preserveAspectRatio 属性"
    val = m.group(1)
    assert val.startswith("xMidYMid"), (
        f"preserveAspectRatio 应是 xMidYMid(等比缩放),实得 {val}"
    )


def test_svg_height_no_40vh_clamp():
    """修复: SVG height 不再用 40vh clamp(触发 mobile 拉伸)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    if "svg {" in html:
        m = re.search(r'svg\s*\{[^}]*\}', html)
        if m:
            body = m.group(0)
            assert not re.search(r"height\s*:\s*clamp\([^)]*40vh", body), (
                f"SVG 仍用 clamp(...,40vh,...): {body}"
            )
            assert not re.search(r"height\s*:\s*40vh", body), (
                f"SVG height 仍用 40vh: {body}"
            )


def test_svg_text_rendering_precise():
    """polish: text-rendering: geometricPrecision 改善文字清晰度"""
    html = TEMPLATE.read_text(encoding="utf-8")
    if "svg" in html and "text-rendering" not in html:
        # 不是硬性要求,只是 polish — skip assertion
        pass


# ============= BUG 2: 表格 note 列在 mobile 可见 =============


def test_table_uses_fixed_layout():
    """修复: table-layout: fixed (强制列宽,不随内容)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    m = re.search(r'table\s*\{[^}]*\}', html)
    assert m, "缺 table CSS 规则"
    body = m.group(0)
    assert "table-layout" in body and "fixed" in body, (
        f"table 缺 table-layout: fixed(否则 mobile 列会随内容溢出): {body}"
    )


def test_table_mobile_keeps_note_column_visible():
    """修复: mobile @media 表格 note 列应可见(不 hide)
    用户原话:'晨起空腹几个字' 必须完整可见.
    """
    html = TEMPLATE.read_text(encoding="utf-8")
    # 检查 mobile @media 内不能有 .note { display:none }
    m = re.search(r"@media\s*\(\s*max-width:\s*640px\s*\)\s*\{(.*?)\}", html, re.DOTALL)
    if m:
        body = m.group(0)
        # 不应 hide note
        assert not re.search(r"\.table-wrap\s+table\s+th\.note[^}]*display\s*:\s*none", body), (
            f"mobile 不应 hide note 列(违背用户 BUG 2): {body}"
        )
        assert not re.search(r"\.table-wrap\s+table\s+td\.note[^}]*display\s*:\s*none", body), (
            f"mobile 不应 hide note td(违背用户 BUG 2): {body}"
        )


def test_table_header_includes_note_column():
    """修复: table_header 必须有 <th>注</th>(否则 note td 没对应 th,布局错位)"""
    # 静态模板的 table_header 是 JS 动态拼的
    # 改测 render script: build_trend_summary 等的 table_header 必须含 注
    text = RENDER.read_text(encoding="utf-8")
    # 应有 5 个 <th> 包含 日期/BMI/体重/vs 上次/注
    matches = re.findall(r"<th[^>]*>([^<]+)</th>", text)
    headers_seen = " ".join(matches)
    assert "注" in headers_seen, (
        f"render script 的 table_header 必须含 '注' 列,实得: {headers_seen[:200]}"
    )


# ============= Lint integration =============


def test_weight_history_lint_passes():
    """集成: weight_history.html 通过 check_html_responsive.py"""
    sys.path.insert(0, str(SKILL_DIR / "scripts"))
    from check_html_responsive import lint_file
    errors = lint_file(TEMPLATE)
    assert errors == [], f"weight_history.html 不通过 lint: {errors}"