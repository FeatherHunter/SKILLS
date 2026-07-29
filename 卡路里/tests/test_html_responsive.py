#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_html_responsive.py — seam 6 守门

ticket 02 · 2026-07-29

覆盖 check_html_responsive.py 三个核心断言:
  1. mobile-safe 模板(已有 @media)→ lint PASSED
  2. 缺 @media 的合成模板 → lint FAILED + 报具体错
  3. SVG 固定像素高度 → lint FAILED + 报 SVG 行
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"


def _run_lint(template_paths: list[str]) -> subprocess.CompletedProcess:
    """用合成 template 跑 lint 脚本

    思路:把 spec'd 模板路径临时放到 --include 参数(若脚本支持);
    若不支持,直接测试 unit 入口函数更可靠。

    这里测的是 CLI 端到端:subprocess 跑,exit code + stdout/stderr 断言。
    """
    # check_html_responsive.py 默认扫 templates/*.html
    # 临时把模板移到子目录,跑 lint 后恢复
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "check_html_responsive.py")],
        cwd=SKILL_DIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=30,
    )


def test_lint_passes_for_mobile_safe_template(tmp_path, monkeypatch):
    """合成一个 mobile-safe 模板,断言 lint exit 0"""
    # 准备模板:含 viewport meta + @media + SVG clamp + table wrap
    mobile_safe = """<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  @media (max-width:640px) { .grid { grid-template-columns: 1fr; } }
  svg { width:100%; height:clamp(180px, 40vh, 320px); }
</style>
</head><body>
<div class="table-wrap" style="overflow-x:auto"><table><tr><td>x</td></tr></table></div>
<svg viewBox="0 0 100 100"></svg>
</body></html>"""

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "test_mobile.html").write_text(mobile_safe, encoding="utf-8")

    # 通过 PYTHONPATH 注入 import path + 用 unit 入口
    sys.path.insert(0, str(SCRIPTS_DIR))
    from check_html_responsive import lint_templates
    errors = lint_templates(templates_dir)
    assert errors == [], f"mobile-safe 模板应通过,实得 errors: {errors}"


def test_lint_fails_when_missing_media_query(tmp_path):
    """合成缺 @media 的模板,断言 lint 报具体错"""
    bad = """<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body { padding: 20px; }
</style>
</head><body>
<div class="table-wrap" style="overflow-x:auto"><table><tr><td>x</td></tr></table></div>
<svg viewBox="0 0 100 100" style="width:100%; height:clamp(180px, 40vh, 320px)"></svg>
</body></html>"""

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "test_bad.html").write_text(bad, encoding="utf-8")

    sys.path.insert(0, str(SCRIPTS_DIR))
    from check_html_responsive import lint_templates
    errors = lint_templates(templates_dir)
    assert any("media" in e.lower() or "@media" in e for e in errors), (
        f"缺 @media 应报错,实得: {errors}"
    )


def test_lint_fails_for_fixed_pixel_svg_height(tmp_path):
    """合成 SVG 用固定像素高度的模板,断言 lint 报 SVG 错"""
    bad = """<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  @media (max-width:640px) { .grid { grid-template-columns: 1fr; } }
  svg { width:100%; height:260px; }
</style>
</head><body>
<div class="table-wrap" style="overflow-x:auto"><table><tr><td>x</td></tr></table></div>
<svg viewBox="0 0 100 100"></svg>
</body></html>"""

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "test_svg.html").write_text(bad, encoding="utf-8")

    sys.path.insert(0, str(SCRIPTS_DIR))
    from check_html_responsive import lint_templates
    errors = lint_templates(templates_dir)
    assert any("svg" in e.lower() for e in errors), (
        f"固定像素 SVG 高度应报错,实得: {errors}"
    )
