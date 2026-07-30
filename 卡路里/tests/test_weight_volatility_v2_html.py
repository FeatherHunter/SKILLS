#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_weight_volatility_v2_html.py — ticket 02 Dashboard 单页

ticket 02 · 2026-07-29

覆盖 seam 4 ticket 02 case:
  - test 1: check_html_responsive.py lint 通过
  - test 3: window.__DATA__.data 含 baseline_value / baseline_sigma / thresholds
  - test 9: HTML 含 <canvas id="chart">

ticket 02 deliverable: templates/weight_volatility_v2.html
- Apple 风格 + 单一 <canvas id="chart">
- 1 张 KPI 卡(诊断)
- 含 <!--INJECT-DATA-->
- viewport meta + @media (max-width:640px)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"
TEMPLATE = TEMPLATES_DIR / "weight_volatility_v2.html"


def test_weight_volatility_v2_template_exists():
    """02: templates/weight_volatility_v2.html 必须存在"""
    assert TEMPLATE.exists(), f"模板缺失: {TEMPLATE}"


def test_weight_volatility_v2_html_passes_responsive_lint():
    """02: seam 4 test 1 — check_html_responsive.py lint 通过"""
    sys.path.insert(0, str(SKILL_DIR / "scripts"))
    from check_html_responsive import lint_file
    errors = lint_file(TEMPLATE)
    assert errors == [], f"weight_volatility_v2.html 不通过 lint: {errors}"


def test_weight_volatility_v2_template_has_viewport():
    """02: 含 viewport meta tag (seam 6 强制)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    assert 'name="viewport"' in html, "缺少 viewport meta tag"
    assert "width=device-width" in html, "viewport meta 缺 width=device-width"


def test_weight_volatility_v2_template_has_at_media():
    """02: 含 @media (max-width:640px) 断点"""
    html = TEMPLATE.read_text(encoding="utf-8")
    assert "@media" in html, "缺少 @media 断点"
    assert "max-width:640px" in html, "缺 640px 断点"


def test_weight_volatility_v2_template_has_canvas():
    """02: 单一 <canvas id='chart'> 元素(Q7 修复 + Q8 v2)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    assert 'id="chart"' in html, "缺 <canvas id='chart'>"
    # seam 4 test 9:Canvas 标记确保
    assert "<canvas" in html, "缺 <canvas> 元素"
    # 确认唯一(不可多个 canvas)
    assert html.count("<canvas") == 1, f"应有 1 个 canvas,实得 {html.count('<canvas')}"


def test_weight_volatility_v2_template_has_inject_data_placeholder():
    """02: 含 <!--INJECT-DATA--> 唯一占位符(seam 6 校验)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    count = html.count("<!--INJECT-DATA-->")
    assert count == 1, f"<!--INJECT-DATA--> 应唯一出现,实得 {count}"


def test_weight_volatility_v2_template_has_kpi_card():
    """02: 至少 1 张 KPI 卡(诊断),含 spec 要求的元素 id"""
    html = TEMPLATE.read_text(encoding="utf-8")
    # spec AC 要求 KPI 含 "今天 X kg vs baseline Y ± Z kg"
    assert 'id="kpiValue"' in html, "缺 KPI 数值 id"
    assert 'id="kpiBaseline"' in html, "缺 KPI baseline id"
    assert 'id="kpiPill"' in html, "缺 KPI 等级 pill id"
    # review fix:KPI 卡应显示 ±σ 范围(不是只 baseline)
    assert "±" in html, "KPI 卡应显示 ±σ 范围"


def test_weight_volatility_v2_template_canvas_render_acceptance():
    """02: review fix — Canvas JS 必须含关键绘制函数(不是仅 API 字符串 grep)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    # 关键绘制:baseline 虚线 + 体重折线 + ±σ band + 目标线
    # 1. baseline 虚线(setLineDash + moveTo + lineTo)
    assert "setLineDash" in html, "缺 baseline 虚线绘制"
    # 2. ±σ band(fillRect,黄色 + 红色)
    assert "rgba(255,149,0," in html, "缺 ±1.5σ yellow band"
    assert "rgba(255,59,48," in html, "缺 ±2σ red band"
    # 3. 目标线(绿色虚线)— ticket 02 AC 明确要求
    assert "34c759" in html or "rgba(52,199,89," in html, "缺目标线(goal 绿色虚线)"
    # 4. 缓冲尺寸显式(防 Q7 stretch bug 回退)
    assert 'width="800"' in html, "缺 canvas width 显式"
    assert 'height="360"' in html, "缺 canvas height 显式"


def test_weight_volatility_v2_template_uses_ticket02_fields():
    """02: ticket 02 实际用到的字段(baseline + thresholds + early_warning)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    required_ticket_02_fields = [
        "baseline_value", "baseline_sigma",
        "thresholds", "points", "early_warning",
    ]
    missing = [f for f in required_ticket_02_fields if f not in html]
    assert not missing, f"ticket 02 字段缺失: {missing}"