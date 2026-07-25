#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_body_photo_gif_planner.py — 身材照 GIF planner HTML 渲染器(v1.0)

对应 SKILL.md 唤醒词:生成身材照GIF

数据源:body_photos 表(根据 URL 参数 ?ids=12,15,22 注入指定照片)
用法:
    python scripts/render_body_photo_gif_planner.py --ids 12,15,22
    python scripts/render_body_photo_gif_planner.py --ids 12,15 --tags 正面 --output /path/out.html
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from html_paths import html_path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'body_photo_gif_planner.html'
DB_FILENAME = "calorie_data.db"

sys.path.insert(0, str(SCRIPT_DIR))
from db import find_db_path, get_db  # noqa


def get_photos_by_ids(ids: list) -> list:
    if not ids:
        return []
    conn = get_db(find_db_path(SKILL_DIR, DB_FILENAME))
    cur = conn.cursor()
    placeholders = ','.join('?' * len(ids))
    cur.execute(f"""
        SELECT id, date, time, photo_path, tag, note
        FROM body_photos
        WHERE id IN ({placeholders})
        ORDER BY date ASC, time ASC
    """, ids)
    rows = cur.fetchall()
    conn.close()
    photos = [dict(zip(['id', 'date', 'time', 'photo_path', 'tag', 'note'], r)) for r in rows]
    # 按传入顺序排序
    return sorted(photos, key=lambda p: ids.index(p['id']))


def list_all_photos(days: int = 90) -> list:
    """列出所有照片(用于模板的 all_photos)"""
    conn = get_db(find_db_path(SKILL_DIR, DB_FILENAME))
    cur = conn.cursor()
    from datetime import timedelta
    end_date = datetime.now().date().isoformat()
    start_date = (datetime.now().date() - timedelta(days=days)).isoformat()
    cur.execute("""
        SELECT id, date, time, photo_path, tag, note
        FROM body_photos
        WHERE date >= ? AND date <= ?
        ORDER BY date DESC, time DESC
    """, (start_date, end_date))
    rows = cur.fetchall()
    conn.close()
    return [dict(zip(['id', 'date', 'time', 'photo_path', 'tag', 'note'], r)) for r in rows]


def render(ids: list, output_path: Path) -> Path:
    selected = get_photos_by_ids(ids)
    all_photos = list_all_photos()

    payload = {
        "status": "ok",
        "data": {
            "fetched_at": datetime.now().isoformat(timespec='seconds'),
            "selected_ids": ids,
            "selected_photos": selected,
            "all_photos": all_photos,
        },
        "message": f"身材照 GIF planner · 已选 {len(selected)} 张",
    }

    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    inject_data = f'<script>window.__DATA__ = {json.dumps(payload, ensure_ascii=False)};</script>'
    html = template.replace('<!--INJECT-DATA-->', inject_data)

    output_path.write_text(html, encoding='utf-8')
    return output_path


def main():
    p = argparse.ArgumentParser(description='渲染身材照 GIF planner HTML')
    p.add_argument('--ids', help='逗号分隔的照片 ID(从 gallery 多选带入)。与 --tag 二选一')
    p.add_argument('--tag', help='按 tag 拉所有照片(独立运行模式,无需先经 gallery)')
    p.add_argument('--tags', help='逗号分隔的 tag(用于输出文件名)')
    p.add_argument('--output', help='输出文件路径')
    args = p.parse_args()

    if not args.ids and not args.tag:
        p.error('必须提供 --ids 或 --tag 之一')

    if args.ids:
        ids = [int(x) for x in args.ids.split(',') if x.strip()]
        suffix = f"ids{'_'.join(str(i) for i in ids)}"
    else:
        # 按 tag 拉所有照片
        conn = get_db(find_db_path(SKILL_DIR, DB_FILENAME))
        cur = conn.cursor()
        cur.execute("SELECT id FROM body_photos WHERE tag = ? ORDER BY date ASC, time ASC", (args.tag,))
        ids = [r[0] for r in cur.fetchall()]
        conn.close()
        suffix = f"tag{args.tag}_n{len(ids)}"
    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, f'body_photo_gif_planner_{suffix}')
    result = render(ids, out_path)
    print(f"✓ 已生成: {result} (已选 {len(ids)} 张)")


if __name__ == '__main__':
    main()