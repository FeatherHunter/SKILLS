#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_food_library.py — ticket 07 验收

ticket 07 · Issue 2 修复(查食品库 默认 50 + TXT → 200 + HTML)

覆盖:
  1. food_library.html 通过 check_html_responsive.py lint
  2. render_food_library.py exit 0
  3. window.__DATA__ 含 total_count + items
  4. 客户端搜索框可工作(ticket 06/07 钩子 5 "复制 prompt"要求的过程型 HTML 必须有 prompt 复制)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
TEMPLATE = SKILL_DIR / "templates" / "food_library.html"
RENDER = SCRIPTS_DIR / "render_food_library.py"


def test_food_library_html_passes_responsive_lint():
    """food_library.html 通过 lint"""
    sys.path.insert(0, str(SCRIPTS_DIR))
    from check_html_responsive import lint_file
    errors = lint_file(TEMPLATE)
    assert errors == [], f"food_library.html 不通过 lint: {errors}"


def _extract_payload(html_text: str) -> dict | None:
    m = re.search(
        r'<script>\s*window\.__DATA__\s*=\s*(\{.*?\});?\s*</script>',
        html_text, re.DOTALL,
    )
    if not m:
        return None
    return json.loads(m.group(1).replace('<\\/', '</'))


def test_render_food_library_exits_zero(temp_db, tmp_path):
    """render_food_library.py → exit 0 + HTML 生成"""
    import sqlite3
    conn = sqlite3.connect(str(temp_db))
    cur = conn.cursor()
    cur.execute("DELETE FROM nutrition_products")
    for i in range(1, 51):
        cur.execute(
            "INSERT INTO nutrition_products"
            "(product_name, brand, calories, protein, fat, carbohydrates, sodium) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (f"测试食品_{i:03d}", "test", 100.0, 5.0, 2.0, 10.0, 50.0),
        )
    conn.commit()
    conn.close()

    out = tmp_path / "food_library.html"
    r = subprocess.run(
        [sys.executable, str(RENDER), "--output", str(out)],
        cwd=SKILL_DIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=30,
        env={**os.environ},
    )
    assert r.returncode == 0, (
        f"render_food_library.py exit={r.returncode}, stderr={r.stderr}"
    )
    assert out.exists(), f"output 不存在: {out}"


def test_food_library_data_shape(temp_db, tmp_path):
    """window.__DATA__ 含 total_count + items + page_size"""
    import sqlite3
    conn = sqlite3.connect(str(temp_db))
    cur = conn.cursor()
    cur.execute("DELETE FROM nutrition_products")
    for i in range(1, 51):
        cur.execute(
            "INSERT INTO nutrition_products"
            "(product_name, brand, calories, protein, fat, carbohydrates, sodium) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (f"测试_{i:03d}", "test", 100.0, 5.0, 2.0, 10.0, 50.0),
        )
    conn.commit()
    conn.close()

    out = tmp_path / "food_library.html"
    subprocess.run(
        [sys.executable, str(RENDER), "--output", str(out)],
        cwd=SKILL_DIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=30,
        env={**os.environ}, check=True,
    )
    html = out.read_text(encoding="utf-8")
    payload = _extract_payload(html)
    assert payload, f"HTML 缺 __DATA__: {html[:300]}"
    data = payload.get("data", {})
    assert "total_count" in data, f"__DATA__ 缺 total_count: {data.keys()}"
    assert "items" in data, f"__DATA__ 缺 items"
    assert data["total_count"] == 50, f"total_count 应 50,实得 {data['total_count']}"
    assert len(data["items"]) == 50, f"items 应 50,实得 {len(data['items'])}"


def test_food_library_has_search_box_with_prompt_copy(temp_db, tmp_path):
    """过程型 HTML 必须有"复制 prompt"按钮(总纲钩子 5 · ticket 07 修正)

    用户输入筛选条件后,应能一键复制 "查食品库 + 筛选词" 的 prompt 回 AI。
    """
    import sqlite3
    conn = sqlite3.connect(str(temp_db))
    cur = conn.cursor()
    cur.execute("DELETE FROM nutrition_products")
    for i in range(1, 11):
        cur.execute(
            "INSERT INTO nutrition_products"
            "(product_name, brand, calories, protein, fat, carbohydrates, sodium) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (f"测试_{i}", "test", 100.0, 5.0, 2.0, 10.0, 50.0),
        )
    conn.commit()
    conn.close()

    out = tmp_path / "food_library.html"
    subprocess.run(
        [sys.executable, str(RENDER), "--output", str(out)],
        cwd=SKILL_DIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=30,
        env={**os.environ}, check=True,
    )
    html = out.read_text(encoding="utf-8")
    # 搜索框
    assert 'id="searchInput"' in html or 'type="search"' in html, (
        "应有搜索输入框"
    )
    # 复制 prompt 按钮(总纲钩子 5 · ticket 06/07 自查发现的 gap)
    assert "复制" in html or "copy" in html.lower(), (
        "应有 '复制 prompt' 按钮(总纲钩子 5 要求)"
    )