#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/render_food_library.py — 食品库全列表 HTML 渲染器

ticket 07 · ADR-0005 部分 · Issue 2 修复

CLI:
    python scripts/render_food_library.py [--limit N | --all] [--output <path>]

与 list-products CLI 同源,但输出 HTML 而非 text。默认 limit 200。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
import db as db_mod  # noqa: E402

TEMPLATE_PATH = SKILL_DIR / "templates" / "food_library.html"


def _query_products(limit: int) -> tuple[list[dict], int]:
    """查全部食品 + 总数"""
    db_path = db_mod.find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM nutrition_products WHERE is_deprecated = 0")
        total_count = c.fetchone()[0]
        c.execute(
            "SELECT id, product_name, brand, calories, protein, fat, carbohydrates, "
            "saturated_fat, sugar, dietary_fiber, sodium, source, updated_at "
            "FROM nutrition_products "
            "WHERE is_deprecated = 0 "
            "ORDER BY id ASC "
            "LIMIT ?",
            (limit,),
        )
        rows = c.fetchall()
        return [dict(r) for r in rows], total_count
    finally:
        conn.close()


def _default_output_path() -> Path:
    """默认输出路径:calorie_html/查食品库_<TS>.html"""
    skills_db = os.environ.get("SKILLS_DB_PATH")
    if skills_db:
        base = Path(skills_db) / "calorie_html"
    else:
        base = db_mod.find_db_path(SKILL_DIR).parent / "calorie_html"
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return base / f"查食品库_{ts}.html"


def _inject_data(html: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return html.replace(
        "<!--INJECT-DATA-->",
        f'<script>window.__DATA__ = {payload};</script>',
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="渲染食品库 HTML")
    parser.add_argument("--limit", type=int, default=200, help="默认 200")
    parser.add_argument("--all", action="store_true", help="全量(覆盖 --limit)")
    parser.add_argument("--page-size", type=int, default=50, help="前端分页 50/页")
    parser.add_argument("--output", help="输出 HTML 路径")
    args = parser.parse_args()

    limit = 999999 if args.all else args.limit
    items, total_count = _query_products(limit)
    data = {
        "status": "ok",
        "data": {
            "items": items,
            "total_count": total_count,
            "page_size": args.page_size,
            "limit_applied": limit if not args.all else None,
            "generated_at": datetime.now().isoformat(),
        },
        "message": f"共 {total_count} 条,本页展示 {len(items)} 条",
    }

    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    html = _inject_data(html, data)

    out = Path(args.output) if args.output else _default_output_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"✓ HTML 已生成: {out}")
    print(f"⚠️ ACTION=SEND_TO_USER | HTML={out.absolute()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())