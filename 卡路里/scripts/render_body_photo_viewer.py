#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_body_photo_viewer.py — 单图查看 HTML 渲染器(v1.0)

对应 SKILL.md 唤醒词:查身材照(单图子路径)

数据源:body_photos 表 + 文件路径
用法:
    python scripts/render_body_photo_viewer.py --id 5
    python scripts/render_body_photo_viewer.py --id 5 --output /path/out.html
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from html_paths import html_path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'body_photo_viewer.html'
DB_FILENAME = "calorie_data.db"

sys.path.insert(0, str(SCRIPT_DIR))
from db import find_db_path, get_db  # noqa


def get_photo(photo_id: int) -> dict:
    conn = get_db(find_db_path(SKILL_DIR, DB_FILENAME))
    cur = conn.cursor()
    cur.execute("""
        SELECT id, date, time, photo_path, tag, note
        FROM body_photos WHERE id = ?
    """, (photo_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return dict(zip(['id', 'date', 'time', 'photo_path', 'tag', 'note'], row))


def get_neighbor_ids(photo_id: int, tag: str) -> tuple:
    """返回同 tag 下 prev / next 照片 ID(按日期排序)"""
    conn = get_db(find_db_path(SKILL_DIR, DB_FILENAME))
    cur = conn.cursor()
    cur.execute("""
        SELECT id FROM body_photos
        WHERE tag = ?
        ORDER BY date ASC, time ASC
    """, (tag,))
    ids = [r[0] for r in cur.fetchall()]
    conn.close()
    idx = ids.index(photo_id) if photo_id in ids else -1
    prev_id = ids[idx - 1] if idx > 0 else None
    next_id = ids[idx + 1] if 0 <= idx < len(ids) - 1 else None
    return prev_id, next_id


def render(photo_id: int, output_path: Path) -> Path:
    photo = get_photo(photo_id)
    if not photo:
        raise ValueError(f"照片 ID={photo_id} 不存在")

    prev_id, next_id = get_neighbor_ids(photo_id, photo['tag'])

    payload = {
        "status": "ok",
        "data": {
            "fetched_at": datetime.now().isoformat(timespec='seconds'),
            "photo": photo,
            "prev_id": prev_id,
            "next_id": next_id,
        },
        "message": "身材照单图查看",
    }

    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    inject_data = f'<script>window.__DATA__ = {json.dumps(payload, ensure_ascii=False)};</script>'
    html = template.replace('<!--INJECT-DATA-->', inject_data)

    output_path.write_text(html, encoding='utf-8')
    return output_path


def emit_send_protocol(output_path: Path):
    """stdout 末行:V1.3 §HTML 交付协议 - Agent 必须 send 给用户"""
    print(f"⚠️ ACTION=SEND_TO_USER | HTML={output_path.absolute()}")


def main():
    p = argparse.ArgumentParser(description='渲染身材照单图查看 HTML')
    p.add_argument('--id', type=int, required=True, help='照片 ID')
    p.add_argument('--output', help='输出文件路径')
    args = p.parse_args()

    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, f'body_photo_viewer_id{args.id}')
    result = render(args.id, out_path)
    print(f"✓ 已生成: {result}")
    emit_send_protocol(result)


if __name__ == '__main__':
    main()