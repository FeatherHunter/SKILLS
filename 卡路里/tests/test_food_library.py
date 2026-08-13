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
        r'<script id="payload" type="application/json">(.*?)</script>',
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
    """payload 含 total_count + items + page_size + Base 信封"""
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
    assert payload, f"HTML 缺 payload 注入: {html[:300]}"
    data = payload.get("data", {})
    assert "total_count" in data, f"payload 缺 total_count: {data.keys()}"
    assert "items" in data, f"payload 缺 items"
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


def test_food_library_text_mode_handles_null_brand(temp_db, tmp_path):
    """Phase 3e.2: --text 输出不能因 brand IS NULL crash

    实测:diet/蔬果/调味品类多数 brand 为 NULL,旧实现 it.get('brand','—')[:10]
    因 dict.get 没覆盖 None 值会抛 TypeError。
    """
    import sqlite3
    conn = sqlite3.connect(str(temp_db))
    cur = conn.cursor()
    cur.execute("DELETE FROM nutrition_products")
    rows = [
        ("有品牌_1", "可口可乐", 100.0, 5.0, 2.0, 10.0, 50.0),
        ("无品牌_1", None,        100.0, 5.0, 2.0, 10.0, 50.0),
        ("无品牌_2", None,        200.0, 8.0, 3.0, 15.0, 80.0),
        ("无品牌_3", "",          300.0, 10.0, 5.0, 20.0, 100.0),
        ("有品牌_2", "百事",       150.0, 6.0, 2.5, 12.0, 60.0),
    ]
    for name, brand, cal, prot, fat, carb, sod in rows:
        cur.execute(
            "INSERT INTO nutrition_products"
            "(product_name, brand, calories, protein, fat, carbohydrates, sodium) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, brand, cal, prot, fat, carb, sod),
        )
    conn.commit()
    conn.close()

    r = subprocess.run(
        [sys.executable, str(RENDER), "--text", "--limit", "10"],
        cwd=SKILL_DIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=30,
        env={**os.environ}, check=False,
    )
    assert r.returncode == 0, f"--text 应 exit 0,实得 {r.returncode}, stderr={r.stderr}"
    # 过滤 header + footer:仅算产品行(数字开头 + 4 空格分隔)
    import re
    data_lines = [l for l in r.stdout.splitlines() if l and not l.startswith("#")]
    # 过滤掉空行
    data_lines = [l for l in data_lines if l.strip()]
    assert len(data_lines) == 5, f"应输出 5 行数据,实得 {len(data_lines)}: {data_lines}"
    assert "—" in r.stdout, "NULL brand 应显示 —"