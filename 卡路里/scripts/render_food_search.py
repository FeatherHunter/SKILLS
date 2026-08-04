#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/render_food_search.py — 食物热量查询 HTML 渲染器

ticket 06 · ADR-0005 部分 · Issue 1 修复

CLI:
    python scripts/render_food_search.py --query <term> [--output <path>]
    python scripts/render_food_search.py --category <分类> [--output <path>]   # 查食品(按分类) · ticket #3

查询 nutrition_products 表,匹配 product_name LIKE '%<term>%' 或 category 精确匹配,
渲染成 templates/food_search.html,注入 window.__DATA__。

输出默认:<SKILLS_DB_PATH 或 fallback>/calorie_html/查热量_<YYYYMMDD>_<HHMMSS>.html
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
import db as db_mod  # noqa: E402

TEMPLATE_PATH = SKILL_DIR / "templates" / "food_search.html"


def _query_products(query: str) -> list[dict]:
    """在 nutrition_products 查匹配项"""
    db_path = db_mod.find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        c.execute(
            "SELECT id, product_name, brand, calories, protein, fat, carbohydrates, "
            "saturated_fat, sugar, dietary_fiber, sodium, source, category, updated_at "
            "FROM nutrition_products "
            "WHERE is_deprecated = 0 AND product_name LIKE ? "
            "ORDER BY updated_at DESC",
            (f"%{query}%",),
        )
        rows = c.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _query_by_category(category: str) -> list[dict]:
    """按分类查食品(ticket #3 · D4.2)"""
    db_path = db_mod.find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        c.execute(
            "SELECT id, product_name, brand, calories, protein, fat, carbohydrates, "
            "saturated_fat, sugar, dietary_fiber, sodium, source, category, updated_at "
            "FROM nutrition_products "
            "WHERE is_deprecated = 0 AND category = ? "
            "ORDER BY product_name",
            (category,),
        )
        rows = c.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _default_output_path(query: str) -> Path:
    """默认输出路径:calorie_html/查热量_<TS>.html

    S8:同秒冲突自动追加 _2 / _3 后缀(SKILL.md §"同秒冲突")
    """
    import os
    skills_db = os.environ.get("SKILLS_DB_PATH")
    if skills_db:
        base = Path(skills_db) / "calorie_html"
    else:
        base = db_mod.find_db_path(SKILL_DIR).parent / "calorie_html"
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_q = re.sub(r"[^\w\u4e00-\u9fff]+", "_", query)[:20]
    base_name = f"查热量_{safe_q}_{ts}.html"
    out = base / base_name
    suffix = 2
    while out.exists():
        out = base / f"查热量_{safe_q}_{ts}_{suffix}.html"
        suffix += 1
    return out


def _inject_data(html: str, data: dict) -> str:
    """把 data 注入到 window.__DATA__ 占位符

    S8:断言占位符唯一出现(SKILL.md §"占位符唯一"硬规则)。
    模板若出现 0 或 ≥2 次,直接报错,避免 silent data loss。
    """
    count = html.count("<!--INJECT-DATA-->")
    if count != 1:
        raise ValueError(
            f"templates/food_search.html 占位符 <!--INJECT-DATA--> 出现 {count} 次,"
            f"应为恰好 1 次(SKILL.md § 占位符唯一 规则)。"
        )
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return html.replace(
        "<!--INJECT-DATA-->",
        f'<script>window.__DATA__ = {payload};</script>',
        1,  # 只替换第一个
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="渲染食物热量查询 HTML")
    parser.add_argument("--query", help="查询关键词")
    parser.add_argument("--category", help="按分类查询(查食品(按分类) · ticket #3)")
    parser.add_argument("--output", help="输出 HTML 路径(默认 calorie_html/查热量_<TS>.html)")
    parser.add_argument("--chain", help="AI 思考链注入(meta.chain,不进 UI;复制日志可带出 · R3)")
    args = parser.parse_args()

    if args.category:
        items = _query_by_category(args.category)
        mode = f"category:{args.category}"
        query_label = f"分类:{args.category}"
        q = f"分类_{args.category}"
    else:
        if not args.query:
            parser.error("需要 --query 或 --category 之一")
        items = _query_products(args.query)
        mode = args.query
        query_label = f"关键词:{args.query}"
        q = args.query
    data = {
        "status": "ok",
        "data": {
            "query": mode,
            "query_label": query_label,
            "items": items,
            "match_count": len(items),
            "generated_at": datetime.now().isoformat(),
            "meta": {"chain": args.chain},
        },
        "message": f"找到 {len(items)} 个匹配",
    }

    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    html = _inject_data(html, data)

    out = Path(args.output) if args.output else _default_output_path(q)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"✓ HTML 已生成: {out}")
    print(f"⚠️ ACTION=SEND_TO_USER | HTML={out.absolute()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())