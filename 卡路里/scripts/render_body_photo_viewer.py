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


def embed_photo_as_base64(photo: dict, photos_dir, max_dim: int = 800) -> dict:
    """读取图片 → 缩放 → 转 base64(飞书友好)

    2026-07-25 减体积:max_dim 1200→800, quality 88→75(单图也压)。
    为何需要:Flybook / IM / 任何外部环境打开 HTML 时,相对路径的 <img> 会 broken。
    嵌入 base64 后 HTML 完全自包含。
    """
    try:
        from PIL import Image
        import base64, io
    except ImportError:
        return photo
    fp = photos_dir / photo['photo_path']
    if not fp.exists():
        return photo
    try:
        img = Image.open(fp)
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')
        w, h = img.size
        if max(w, h) > max_dim:
            if w >= h:
                new_w = max_dim; new_h = int(h * max_dim / w)
            else:
                new_h = max_dim; new_w = int(w * max_dim / h)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=75, optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode('ascii')
        photo = dict(photo)
        photo['photo_data_base64'] = f"data:image/jpeg;base64,{b64}"
        photo['photo_embedded_size'] = (img.size[0], img.size[1])
        return photo
    except Exception as e:
        print(f"  ⚠ 无法嵌入 {fp}: {e}")
        return photo


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


def render(photo_id: int, output_path: Path, embed_images: bool = True) -> Path:
    photo = get_photo(photo_id)
    if not photo:
        raise ValueError(f"照片 ID={photo_id} 不存在")

    # V1.3 §HTML 交付协议:base64 嵌图(飞书友好)
    if embed_images:
        from body_photo_tracker import get_photos_dir
        photos_dir = get_photos_dir()
        photo = embed_photo_as_base64(photo, photos_dir)

    prev_id, next_id = get_neighbor_ids(photo_id, photo['tag'])

    # v2.3.4(2026-07-25 fix):__DATA__ 只带 metadata,base64 渲染到 HTML 静态 <img>
    payload = {
        "status": "ok",
        "data": {
            "fetched_at": datetime.now().isoformat(timespec='seconds'),
            "photo_meta": {
                'id': photo['id'],
                'date': photo['date'],
                'time': photo.get('time', ''),
                'tag': photo['tag'],
                'note': photo.get('note', ''),
                'photo_path': photo['photo_path'],
            },
            "prev_id": prev_id,
            "next_id": next_id,
            "embedded": embed_images,
        },
        "message": "身材照单图查看",
    }

    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    inject_data = f'<script>window.__DATA__ = {json.dumps(payload, ensure_ascii=False)};</script>'
    html = template.replace('<!--INJECT-DATA-->', inject_data)

    # Python 渲染时直接给 <img id="mainPhoto"> 填好 base64 src
    main_b64 = photo.get('photo_data_base64', '')
    if main_b64:
        # 替换 <img id="mainPhoto" src="" ...>  →  src="data:..."
        html = html.replace(
            '<img id="mainPhoto" src="" alt="身材照">',
            f'<img id="mainPhoto" src="{main_b64}" alt="身材照">'
        )

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