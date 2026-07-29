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
RENDER = SKILL_DIR / "scripts" / "render_weight_volatility_v2.py"
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
    """02: 至少 1 张 KPI 卡(诊断)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    # 至少 1 个 KPI 标识(class 或 id)
    assert "kpi" in html.lower(), "缺 KPI 标记"
    # 含 baseline_value 占位符
    assert "baseline_value" in html or "baseline" in html, "缺 baseline 引用"


def test_weight_volatility_v2_template_canvas_render_acceptance():
    """02: 视觉:demo 时 render 默认数据后,Canvas 内可见 baseline / 体重线 / ±σ 带阴影

    Canvas 渲染是 JS 端,静态 HTML 验证 JS 代码存在 + 含关键绘制函数。
    """
    html = TEMPLATE.read_text(encoding="utf-8")
    # JS 必须在 <script> 块内
    assert "<script>" in html or "<script " in html
    # 含 Canvas 绘制 API
    assert "canvas" in html.lower()
    # 关键 Canvas API 调用
    canvas_apis = ["getContext", "fillRect", "fillText", "stroke", "beginPath", "moveTo"]
    found_apis = [api for api in canvas_apis if api in html]
    assert len(found_apis) >= 3, (
        f"Canvas 绘制 API 覆盖不足,找到 {len(found_apis)} 个: {found_apis}"
    )


def test_weight_volatility_v2_template_uses_spec_data_fields():
    """02: 含 spec §Implementation Decisions 要求的 data 字段占位符"""
    html = TEMPLATE.read_text(encoding="utf-8")
    # 这些字段都得在 JS 或 HTML 中被引用
    required_fields = [
        "baseline_value", "baseline_sigma",
        "thresholds", "points", "recent_anomalies", "sigma_trend",
        "early_warning", "baseline_toggle_label",
    ]
    missing = [f for f in required_fields if f not in html]
    assert not missing, f"模板缺 spec data 字段: {missing}"