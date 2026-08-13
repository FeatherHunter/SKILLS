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

from _base_render import render_template, write_html  # noqa: E402

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
    """默认输出路径:calorie_html/查食品库_<TS>.html

    S8:同秒冲突自动追加 _2 / _3 后缀(SKILL.md §"同秒冲突")
    """
    skills_db = os.environ.get("SKILLS_DB_PATH")
    if skills_db:
        base = Path(skills_db) / "calorie_html"
    else:
        base = db_mod.find_db_path(SKILL_DIR).parent / "calorie_html"
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"查食品库_{ts}.html"
    out = base / base_name
    suffix = 2
    while out.exists():
        out = base / f"查食品库_{ts}_{suffix}.html"
        suffix += 1
    return out


def _inject_data(html: str, data: dict) -> str:
    """S8:占位符唯一性校验 → Base 管线注入"""
    if html.count("<!--INJECT-DATA-->") != 1:
        raise ValueError(
            f"templates/food_library.html 占位符 <!--INJECT-DATA--> 出现异常,"
            f"应为恰好 1 次(SKILL.md § 占位符唯一 规则)。"
        )
    return render_template(TEMPLATE_PATH, data, "查食品库")


def main() -> int:
    parser = argparse.ArgumentParser(description="渲染食品库 HTML")
    parser.add_argument("--limit", type=int, default=200, help="默认 200")
    parser.add_argument("--all", action="store_true", help="全量(覆盖 --limit)")
    parser.add_argument("--page-size", type=int, default=50, help="前端分页 50/页")
    parser.add_argument("--text", action="store_true",
                        help="Phase 3e: 纯文本输出 pipeline 友好(默认输出 HTML)")
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

    # Phase 3e --text:纯文本输出 pipeline 模式(对应 ticket 07 M4 + R2 缓解)
    if args.text:
        sys.stdout.write("# MODE=text · 适用: ... | grep / awk / wc-l 等 pipeline\n")
        for it in items:
            brand = it.get('brand') or '—'
            sys.stdout.write(
                f"{it['id']:>5}  {(it.get('product_name') or '')[:30]:<30}  {brand[:10]:<10}  "
                f"热 {it.get('calories', 0):>5} 蛋 {it.get('protein', 0):>4.1f}  "
                f"脂 {it.get('fat', 0):>4.1f} 碳 {it.get('carbohydrates', 0):>5.1f}\n"
            )
        sys.stdout.write(f"# 共 {total_count} 条 · 本次输出 {len(items)} 条\n")
        return 0

    write_html(html, out)
    print(f"✓ HTML 已生成: {out}")
    print(f"⚠️ ACTION=SEND_TO_USER | HTML={out.absolute()}")
    return 0


if __name__ == "__main__":
    from _io_guard import guard_io; guard_io()
    sys.exit(main())