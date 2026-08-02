#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_trigger_consistency_html_first.py — ticket 09 seam 守门

ticket 09 · check_trigger_consistency.py 升级为 HTML-First 强制校验

覆盖:
  1. 现有 trigger 一致性不退化(原 3-edge check 仍 pass)
  2. §触发词速查表 + §已实现模板表 + §⚠️ 强制性规定 同步反映新增 trigger/模板/规则
  3. ADR-0004 / 0005 / 0006 / 0007 都在 docs/adr/
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
SKILL_MD = SKILL_DIR / "SKILL.md"
ADR_DIR = SKILL_DIR / "docs" / "adr"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def test_trigger_consistency_checker_passes():
    """scripts/check_trigger_consistency.py 自检 exit 0(不退化)"""
    r = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "check_trigger_consistency.py")],
        cwd=SKILL_DIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=30,
    )
    assert r.returncode == 0, (
        f"check_trigger_consistency.py exit={r.returncode}\n"
        f"stdout: {r.stdout}\nstderr: {r.stderr}"
    )


def test_skill_md_template_list_includes_food_search():
    """§已实现模板表 含 food_search.html(ADR-0005 部分)"""
    text = _read(SKILL_MD)
    assert "food_search.html" in text or "food_search" in text, (
        "§已实现模板表 应列 food_search.html"
    )


def test_skill_md_template_list_includes_food_library():
    """§已实现模板表 含 food_library.html"""
    text = _read(SKILL_MD)
    assert "food_library.html" in text or "food_library" in text, (
        "§已实现模板表 应列 food_library.html"
    )


def test_skill_md_trigger_table_lists_food_search_cli():
    """§触发词速查表 含 查食品 → render_food_search.py(2026-08-02 改:旧词 查热量 退役,新词 查食品)"""
    text = _read(SKILL_MD)
    m = re.search(r"^\| 查食品 \|[^|]*\|.*?python scripts/[^\s|]+", text, re.MULTILINE)
    assert m and "render_food_search" in m.group(0), (
        f"查食品 行的 CLI 列应是 render_food_search.py,实得: {m.group(0)[:200] if m else 'no match'}"
    )


def test_skill_md_trigger_table_lists_food_library_cli():
    """§触发词速查表 含 看食品库（去重） → render_dedupe_report.py(2026-08-02 改:旧词 查食品库 退役)"""
    text = _read(SKILL_MD)
    m = re.search(r"^\| 看食品库（去重） \|[^|]*\|.*?python scripts/[^\s|]+", text, re.MULTILINE)
    assert m and "render_dedupe_report" in m.group(0), (
        f"看食品库（去重） 行的 CLI 列应是 render_dedupe_report.py,实得: {m.group(0)[:200] if m else 'no match'}"
    )


def test_skill_md_has_7_numbered_rules():
    """§⚠️ 强制性规定 7 条编号规则"""
    text = _read(SKILL_MD)
    m = re.search(r"## ⚠️ 强制性规定.*?(?=^## |\Z)", text, re.DOTALL | re.MULTILINE)
    assert m
    section = m.group(0)
    numbered = re.findall(r"^(\d+)\.\s", section, re.MULTILINE)
    assert "7" in numbered, (
        f"§⚠️ 应有编号 7,实得: {numbered}"
    )


def test_adrs_0004_0005_0006_0007_exist():
    """4 个 ADR 文件都存在"""
    for n, name in [
        ("0004", "cli-flag-validation"),
        ("0005", "html-first-default-for-queries"),
        ("0006", "test-db-isolation"),
        ("0007", "ai-verification-protocol"),
    ]:
        path = ADR_DIR / f"{n}-{name}.md"
        assert path.exists(), f"ADR 缺失: {path}"