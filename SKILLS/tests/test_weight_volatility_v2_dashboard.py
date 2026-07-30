#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_weight_volatility_v2_dashboard.py — ticket 03 完整 dashboard

ticket 03 · 2026-07-29

覆盖 seam 4 ticket 03 case:
  - 3 张 KPI 卡(诊断 + 趋势 + 早警告)
  - 异常点列表(最近 7 天,按偏离度倒序,黄/红徽章)
  - 列表空时显示"无异常 ✓"
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "templates" / "weight_volatility_v2.html"


def test_weight_volatility_v2_template_has_three_kpi_sections():
    """03: 3 张 KPI 卡(诊断 + 趋势 + 早警告)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    # 3 个 KPI section:诊断 / 趋势 / 早警告
    assert 'id="kpi-diagnosis"' in html, "缺 KPI 诊断区"
    # 趋势 / 早警告 静态部分(ticket 03)
    assert 'id="kpi-trend"' in html, "缺 KPI 趋势区"
    assert 'id="kpi-early-warning"' in html, "缺 KPI 早警告区"


def test_weight_volatility_v2_template_kpi_trend_uses_sigma_trend():
    """03: 趋势 KPI 应引用 sigma_trend(slope / 收紧 / 扩大)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    # 趋势 KPI 应只用 sigma_trend 字段
    assert "sigma_trend" in html, "缺 sigma_trend 引用(ticket 03 spec use case B)"
    # 而非 baseline_value 这类绝对值
    assert "早 σ" in html or "σ 缩小" in html or "近 7 天 σ" in html or "σ 趋势" in html, (
        "KPI 趋势区应有解读文案"
    )


def test_weight_volatility_v2_template_anomaly_list_present():
    """03: 异常点列表(<div id='anomaliesList'>)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    assert 'id="anomaliesList"' in html, "缺异常列表容器 id='anomaliesList'"
    # 列表有标题
    assert "异常" in html, "缺异常列表标题"


def test_weight_volatility_v2_template_anomaly_structure_supports_loop():
    """03: 异常列表使用 recent_anomalies 数据循环渲染"""
    html = TEMPLATE.read_text(encoding="utf-8")
    # JS 应有 recent_anomalies.map 或类似循环
    assert "recent_anomalies" in html, "缺 recent_anomalies 数据引用"
    # 应有 map 或 forEach
    has_loop = "recent_anomalies.map" in html or "recent_anomalies.forEach" in html or "for (const a of" in html
    assert has_loop, "缺异常列表循环渲染"


def test_weight_volatility_v2_template_anomaly_level_color():
    """03: 异常点徽章 yellow/red/normal(spec use case C)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    # 黄色 + 红色 + 绿色徽章(spec 一致)
    assert "#ff9500" in html or "rgba(255,149,0" in html, "缺黄色徽章"
    assert "#ff3b30" in html or "rgba(255,59,48" in html, "缺红色徽章"
    assert "#34c759" in html or "rgba(52,199,89" in html, "缺绿色正常徽章"


def test_weight_volatility_v2_template_anomaly_empty_state():
    """03: 异常列表空时显示"无异常 ✓" """
    html = TEMPLATE.read_text(encoding="utf-8")
    # 需有 if recent_anomalies.length === 0 的分支
    has_empty = ("length === 0" in html or "length == 0" in html or "无异常" in html)
    assert has_empty, "缺异常列表空态提示(>0 近期异常 ✓)"


def test_weight_volatility_v2_template_anomaly_v2_3_use_case_story():
    """03: 验证 use case C 故事 — 列表按 recent_anomalies date + level 渲染"""
    # 不需要测业务逻辑(那是 backend 的事),只测模板具备渲染能力
    html = TEMPLATE.read_text(encoding="utf-8")
    # 应有 date 的显示
    assert "date" in html, "缺 date 字段渲染"
    # 应有 deviation 的显示
    assert "deviation" in html, "缺 deviation 字段渲染(异常列表要显示偏差)"
    # 应有 kg 字段
    assert "kg" in html, "缺 kg 字段渲染"


def test_weight_volatility_v2_template_v2_3_acceptance_demoable():
    """03: 整合验收 — 当 §Implementation Decisions 3 个 use case 全部渲染时

    验证基础结构:
    - 顶部 3 KPI 自动更新
    - 中部 Canvas 已存在(02 落地)
    - 底部异常列表容器就绪
    """
    html = TEMPLATE.read_text(encoding="utf-8")
    # 顶部 3 KPI 区
    assert html.count('class="kpi') >= 3 or html.count('id="kpi-') >= 3, (
        "应有 3 张 KPI 卡(诊断 / 趋势 / 早警告)"
    )
    # 中部 Canvas
    assert 'id="chart"' in html, "缺 Canvas 主图"
    # 底部异常区
    assert "异常" in html, "缺异常列表"
    # 整体 3 段式
    assert "kpi-diagnosis" in html and "anomalies" in html, "缺 3 段式结构"