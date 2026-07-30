#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_weight_volatility_v2_toggle.py — ticket 04 baseline toggle

ticket 04 · 2026-07-29

覆盖 seam 4 ticket 04 case:
  - baseline toggle 按钮(rolling ↔ goal)
  - 点击切换 re-render Canvas + KPI 文字
  - URL `?baseline=rolling` 持久化
  - localStorage 持久化
  - σ 趋势 sparkline(KPI B 内)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "templates" / "weight_volatility_v2.html"


def test_weight_volatility_v2_template_has_toggle_button():
    """04: 模板含 baseline toggle 按钮"""
    html = TEMPLATE.read_text(encoding="utf-8")
    # 按钮 id 或 class(rolling / goal 双 button)
    assert ("toggleBaseline" in html
            or "baseline-toggle" in html
            or "切换 baseline" in html
            or ("toggleRolling" in html and "toggleGoal" in html)), (
        "缺 baseline toggle 按钮"
    )


def test_weight_volatility_v2_template_toggle_buttons_for_both_modes():
    """04: 按钮含两种 mode 选项(rolling / goal)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    # 按钮文案含 rolling 跟 goal
    has_rolling = "rolling" in html and ("滚动" in html or "rolling" in html.lower())
    has_goal = "goal" in html and ("目标" in html or "goal" in html.lower())
    assert has_rolling, "缺 rolling 按钮文案"
    assert has_goal, "缺 goal 按钮文案"


def test_weight_volatility_v2_template_toggle_persistence_url():
    """04: URL `?baseline=rolling` 持久化"""
    html = TEMPLATE.read_text(encoding="utf-8")
    # JS 应读 URL param
    has_url_read = (
        "URLSearchParams" in html
        or "location.search" in html
        or "searchParams" in html
        or "window.location" in html
    )
    assert has_url_read, "缺 URLSearchParams 读 URL param"


def test_weight_volatility_v2_template_toggle_persistence_localstorage():
    """04: localStorage 持久化"""
    html = TEMPLATE.read_text(encoding="utf-8")
    has_ls = "localStorage" in html
    assert has_ls, "缺 localStorage 持久化"


def test_weight_volatility_v2_template_toggle_event_handler():
    """04: 按钮 click event handler — re-render Canvas + KPI"""
    html = TEMPLATE.read_text(encoding="utf-8")
    # addEventListener('click', ...) 或 onclick= 模式
    has_click_handler = (
        "addEventListener" in html
        or "onclick" in html.lower()
    )
    assert has_click_handler, "缺 click event handler"


def test_weight_volatility_v2_template_toggle_rerender_call():
    """04: 切换后 re-render 函数被调用"""
    html = TEMPLATE.read_text(encoding="utf-8")
    # 应有 render() 或 renderChart() 函数
    has_render = "function render" in html or "renderChart" in html or "render(" in html
    assert has_render, "缺 render 函数(切换后要调用)"


def test_weight_volatility_v2_template_sigma_trend_present():
    """04: σ 趋势 sparkline(KPI B 内, spec use case B)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    # sigma_trend 数据应被 KPI #2 使用
    assert "sigma_trend" in html, "缺 sigma_trend 引用"
    # 至少 1 处读 sigma_trend[i] 或 .slice(-7)
    has_sliced = ".slice(" in html and "sigma_trend" in html
    assert has_sliced, "sigma_trend 应有 .slice() 提取最近 N 个"


def test_weight_volatility_v2_template_toggle_label_surfaces():
    """04: 切换后 baseline_toggle_label 应被显示"""
    html = TEMPLATE.read_text(encoding="utf-8")
    assert "baseline_toggle_label" in html, "缺 baseline_toggle_label 引用"


def test_weight_volatility_v2_template_mobile_kpi_grid():
    """04: mobile 单列堆叠(KPI grid)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    # @media (max-width:640px) 应将 kpi-grid 改为 1 列
    has_mobile_kpi = (
        ".kpi-grid" in html
        and "@media" in html
        and "max-width:640px" in html
    )
    assert has_mobile_kpi, "缺 mobile @media 对 kpi-grid 的适配"


def test_weight_volatility_v2_template_mobile_anomaly_list():
    """04: mobile 单列堆叠(异常列表)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    # 异常列表 grid 在 mobile 应 1 列
    has_mobile_anom = (
        ".anomaly-item" in html
        and "@media" in html
        and ("max-width:640px" in html)
    )
    assert has_mobile_anom, "缺 mobile @media 对 anomaly-item 的适配"


def test_weight_volatility_v2_template_sigma_trend_direction():
    """04: σ 趋势方向计算(↓ 缩小 / ↑ 扩大 / → 平稳)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    # 应有方向比较的逻辑
    has_direction = (
        ("σ 缩小" in html)
        or ("σ 扩大" in html)
        or ("缩小" in html and "扩大" in html)
    )
    assert has_direction, "缺 σ 趋势方向计算"