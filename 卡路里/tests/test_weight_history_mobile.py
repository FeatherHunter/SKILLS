#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_weight_history_mobile.py — ticket 05 验收

ticket 05 · Issue 3/4/5 修复

覆盖:
  1. weight_history.html 通过 check_html_responsive.py lint
  2. SVG 高度用 clamp()(非固定像素)
  3. <table> 在 overflow-x:auto 包装内
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
TEMPLATE = SKILL_DIR / "templates" / "weight_history.html"


def test_weight_history_passes_responsive_lint():
    """check_html_responsive.py 对 weight_history.html 报错为 0"""
    sys.path.insert(0, str(SCRIPTS_DIR))
    from check_html_responsive import lint_file
    errors = lint_file(TEMPLATE)
    assert errors == [], (
        f"weight_history.html 不通过 lint,errors: {errors}"
    )


def test_weight_history_svg_uses_clamp_height():
    """SVG 高度用 clamp()(不是固定像素)"""
    text = TEMPLATE.read_text(encoding="utf-8")
    # 找 svg {...} CSS 规则
    assert "svg" in text, "模板应有 svg 元素"
    # 必须有 clamp(...) 或 vh/vw 单位
    assert "clamp(" in text, "SVG 高度应用 clamp() 函数"


def test_weight_history_table_wrapped_in_overflow_div():
    """<table> 在 div.table-wrap(overflow-x:auto)内"""
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "table-wrap" in text, "模板应有 table-wrap class"
    assert "overflow-x:auto" in text.replace(" ", ""), (
        "table-wrap div 应有 overflow-x:auto"
    )
    # <table> 在 <div class="table-wrap" 之后
    assert text.find("table-wrap") < text.find("<table"), (
        "table-wrap div 应在 <table> 之前"
    )