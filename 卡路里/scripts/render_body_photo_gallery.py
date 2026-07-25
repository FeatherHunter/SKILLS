#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_body_photo_gallery.py — 身材照画廊 HTML 渲染器(v1.0)

对应 SKILL.md 唤醒词:查身材照

数据源:body_photos 表(按 tag + 日期范围筛选)
用法:
    python scripts/render_body_photo_gallery.py --days 30
    python scripts/render_body_photo_gallery.py --days 30 --tag 正面
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from html_paths import html_path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'body_photo_gallery.html'
DB_FILENAME = "calorie_data.db"

sys.path.insert(0, str(SCRIPT_DIR))
from db import find_db_path, get_db  # noqa


def list_photos(days: int = 30, tag: str = None) -> list:
    conn = get_db(find_db_path(SKILL_DIR, DB_FILENAME))
    cur = conn.cursor()
    end_date = datetime.now().date().isoformat()
    start_date = (datetime.now().date() - timedelta(days=days)).isoformat()
    if tag and tag != 'all':
        cur.execute("""
            SELECT id, date, time, photo_path, tag, note
            FROM body_photos
            WHERE tag = ? AND date >= ? AND date <= ?
            ORDER BY date DESC, time DESC
        """, (tag, start_date, end_date))
    else:
        cur.execute("""
            SELECT id, date, time, photo_path, tag, note
            FROM body_photos
            WHERE date >= ? AND date <= ?
            ORDER BY date DESC, time DESC
        """, (start_date, end_date))
    rows = cur.fetchall()
    conn.close()
    return [dict(zip(['id', 'date', 'time', 'photo_path', 'tag', 'note'], r)) for r in rows]


def list_tags() -> list:
    conn = get_db(find_db_path(SKILL_DIR, DB_FILENAME))
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT tag FROM body_photos ORDER BY tag")
    tags = [r[0] for r in cur.fetchall()]
    conn.close()
    return tags


def render(days: int, tag: str, output_path: Path) -> Path:
    photos = list_photos(days=days, tag=tag)
    all_tags = list_tags()

    payload = {
        "status": "ok",
        "data": {
            "fetched_at": datetime.now().isoformat(timespec='seconds'),
            "photos": photos,
            "tags": ['all'] + all_tags,
            "current_tag": tag or 'all',
            "days": days,
        },
        "message": "身材照画廊",
    }

    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    inject_data = f'<script>window.__DATA__ = {json.dumps(payload, ensure_ascii=False)};</script>'
    html = template.replace('<!--INJECT-DATA-->', inject_data)

    output_path.write_text(html, encoding='utf-8')
    return output_path


def main():
    p = argparse.ArgumentParser(description='渲染身材照画廊 HTML')
    p.add_argument('--days', type=int, default=30, help='最近 N 天(默认 30)')
    p.add_argument('--tag', default='all', help='按 tag 筛选(all=全部)')
    p.add_argument('--output', help='输出文件路径')
    args = p.parse_args()

    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, f'body_photo_gallery_{args.tag}_{args.days}d')
    result = render(args.days, args.tag, out_path)
    print(f"✓ 已生成: {result} ({len(list_photos(args.days, args.tag))} 张照片)")


if __name__ == '__main__':
    main()