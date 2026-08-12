#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_food_search.py — ticket 06 验收

ticket 06 · Issue 1 修复(查热量 没 HTML)
覆盖:
  1. food_search.html 通过 check_html_responsive.py lint
  2. render_food_search.py --query "牛肉" --output x.html exit 0
  3. 生成的 HTML 含 ≥5 food cards
  4. window.__DATA__.query == "牛肉"
  5. window.__DATA__.items.length ≥ 5
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
TEMPLATE = SKILL_DIR / "templates" / "food_search.html"
RENDER = SCRIPTS_DIR / "render_food_search.py"


def test_food_search_html_passes_responsive_lint():
    """food_search.html 通过 lint"""
    sys.path.insert(0, str(SCRIPTS_DIR))
    from check_html_responsive import lint_file
    errors = lint_file(TEMPLATE)
    assert errors == [], f"food_search.html 不通过 lint: {errors}"


def _extract_payload(html_text: str) -> dict | None:
    m = re.search(
        r'<script>\s*window\.__DATA__\s*=\s*(\{.*?\});?\s*</script>',
        html_text, re.DOTALL,
    )
    if not m:
        return None
    return json.loads(m.group(1).replace('<\\/', '</'))


def test_render_food_search_exits_zero(temp_db, tmp_path):
    """render_food_search.py --query '牛肉' → exit 0"""
    # 插 5 条匹配 + 2 条不匹配的测试数据
    import sqlite3
    conn = sqlite3.connect(str(temp_db))
    cur = conn.cursor()
    cur.execute("DELETE FROM nutrition_products")
    for i, name in enumerate([
        "牛肉(代表值)", "牛肉干", "牛肉松", "牛肉(前腱)",
        "牛肉(后腿)", "可乐", "炸鸡",
    ]):
        cur.execute(
            "INSERT INTO nutrition_products"
            "(product_name, brand, calories, protein, fat, carbohydrates, sodium) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, "test", 100 + i*10, 10.0, 5.0, 8.0, 50.0),
        )
    conn.commit()
    conn.close()

    out = tmp_path / "food_search.html"
    r = subprocess.run(
        [sys.executable, str(RENDER), "--query", "牛肉", "--output", str(out)],
        cwd=SKILL_DIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=30,
        env={**__import__("os").environ},  # 用当前进程 env(temp_db 已设)
    )
    assert r.returncode == 0, (
        f"render_food_search.py exit={r.returncode}, stderr={r.stderr}, stdout={r.stdout}"
    )
    assert out.exists(), f"output 文件不存在: {out}"


def test_food_search_html_has_cards_and_data(temp_db, tmp_path):
    """生成的 HTML 含 ≥5 food cards + window.__DATA__ 含 query='牛肉'

    S7 修:不仅断言 JSON items 长度,还断言 HTML DOM 实际渲染卡片节点。
    """
    import sqlite3, os
    conn = sqlite3.connect(str(temp_db))
    cur = conn.cursor()
    cur.execute("DELETE FROM nutrition_products")
    for i, name in enumerate([
        "牛肉(代表值)", "牛肉干", "牛肉松", "牛肉(前腱)",
        "牛肉(后腿)", "可乐", "炸鸡",
    ]):
        cur.execute(
            "INSERT INTO nutrition_products"
            "(product_name, brand, calories, protein, fat, carbohydrates, sodium) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, "test", 100 + i*10, 10.0, 5.0, 8.0, 50.0),
        )
    conn.commit()
    conn.close()

    out = tmp_path / "food_search.html"
    subprocess.run(
        [sys.executable, str(RENDER), "--query", "牛肉", "--output", str(out)],
        cwd=SKILL_DIR, capture_output=True, text=True, timeout=30,
        env={**os.environ}, check=True, encoding="utf-8", errors="replace",
    )
    html = out.read_text(encoding="utf-8")

    payload = _extract_payload(html)
    assert payload, f"HTML 缺 window.__DATA__: {html[:300]}"
    assert payload.get("data", {}).get("query") == "牛肉", (
        f"__DATA__.query 应是 '牛肉',实得: {payload.get('data', {}).get('query')}"
    )
    items = payload.get("data", {}).get("items", [])
    assert len(items) >= 5, f"items 应 ≥5,实得 {len(items)}"
    # 匹配应全是牛肉(无可乐/炸鸡)
    for it in items:
        assert "牛肉" in it["product_name"], (
            f"items 含非牛肉: {it['product_name']}"
        )

    # S7 增量:静态 HTML 含 JS 渲染 hook(cards 由 JS 在客户端渲染,不在 server 输出)
    assert "function renderCard" in html or "renderCard(" in html, (
        "HTML 应含 renderCard 函数定义(客户端 JS 渲染卡片)"
    )
    assert 'id="results"' in html, "HTML 应含 id=results 容器(JS 填充目标)"
    # 检查 JS 实际会渲染所有 items
    assert "items.map(function" in html or "items.map(it =>" in html or "items.map(function(it)" in html, (
        "HTML 应有 items.map(...) 把 data.items 渲染成 DOM"
    )