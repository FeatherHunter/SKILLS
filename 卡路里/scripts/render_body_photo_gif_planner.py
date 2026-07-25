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


def check_photos_exist(photos: list, photos_dir: Path) -> tuple:
    """检查照片文件是否存在。返回 (existing_photos, missing_ids)"""
    existing, missing = [], []
    for p in photos:
        fp = photos_dir / p['photo_path']
        if fp.exists():
            existing.append(p)
        else:
            missing.append(p['id'])
    return existing, missing


def embed_photo_as_base64(photo: dict, photos_dir: Path, max_dim: int = 800) -> dict:
    """读取图片 → 缩放(保持比例) → 转 base64 JPEG → 写回 photo

    为何需要:Flybook / IM / 任何外部环境打开 HTML 时,相对路径的 <img> 会 broken。
    嵌入 base64 后 HTML 完全自包含。
    """
    try:
        from PIL import Image
        import base64
        import io
    except ImportError:
        return photo  # 没 PIL 时静默跳过,fallback 到 photo_path

    fp = photos_dir / photo['photo_path']
    if not fp.exists():
        return photo
    try:
        img = Image.open(fp)
        # 转 RGB(避免 PNG/RGBA 不能 JPEG)
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')
        # 等比缩放:长边 ≤ max_dim
        w, h = img.size
        if max(w, h) > max_dim:
            if w >= h:
                new_w = max_dim
                new_h = int(h * max_dim / w)
            else:
                new_h = max_dim
                new_w = int(w * max_dim / h)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        # 转 JPEG base64
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85, optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode('ascii')
        photo = dict(photo)  # copy
        photo['photo_data_base64'] = f"data:image/jpeg;base64,{b64}"
        photo['photo_embedded_size'] = (img.size[0], img.size[1])
        return photo
    except Exception as e:
        print(f"  ⚠ 无法嵌入 {fp}: {e}")
        return photo


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


def render(ids: list, output_path: Path, validate_files: bool = True) -> Path:
    selected = get_photos_by_ids(ids)
    all_photos = list_all_photos()

    missing_ids = []
    if validate_files:
        from body_photo_tracker import get_photos_dir
        photos_dir = get_photos_dir()
        # 用 selected 拿 missing 列表
        existing, missing_ids = check_photos_exist(selected, photos_dir)
        # selected 用 existing(去掉缺失的)
        selected_for_display = existing
    else:
        # 未走 validate_files 也要拿 photos_dir 用于 file_url 转换
        from body_photo_tracker import get_photos_dir
        photos_dir = get_photos_dir()
        selected_for_display = selected

    def to_file_url(photo):
        """file:// 绝对 URL(电脑本地 Chrome 能直接打开)"""
        abs_path = (photos_dir / photo['photo_path']).resolve()
        return {**photo, 'photo_path': abs_path.as_uri()}

    # v2.3.3:base64 嵌图(默认开)— 飞书 / IM / 任意环境打开都能看
    # 本地电脑 Chrome 用户可加 --no-embed-images 走 file://
    embed = True  # 默认开,符合 V1.3 + 用户跨设备需求
    if embed:
        selected_for_display = [embed_photo_as_base64(p, photos_dir) for p in selected_for_display]
        all_photos_for_display = []
        for p in all_photos:
            if (photos_dir / p['photo_path']).exists():
                all_photos_for_display.append(embed_photo_as_base64(p, photos_dir))
    else:
        # fallback:转 file:// URL
        selected_for_display = [to_file_url(p) for p in selected_for_display]
        all_photos_for_display = [to_file_url(p) for p in all_photos if (photos_dir / p['photo_path']).exists()]

    payload = {
        "status": "ok",
        "data": {
            "fetched_at": datetime.now().isoformat(timespec='seconds'),
            "selected_ids": ids,
            "selected_photos": selected_for_display,
            "all_photos": all_photos_for_display,
            "missing_ids": missing_ids,
            "missing_count": len(missing_ids),
            "embedded": embed,
        },
        "message": f"身材照 GIF planner · 共 {len(selected_for_display)} 张可用 · 跳过 {len(missing_ids)} 张丢失" + (" · 📦 图片已嵌 base64(飞书友好)" if embed else ""),
    }

    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    inject_data = f'<script>window.__DATA__ = {json.dumps(payload, ensure_ascii=False)};</script>'
    html = template.replace('<!--INJECT-DATA-->', inject_data)

    output_path.write_text(html, encoding='utf-8')
    return output_path


def emit_send_protocol(output_path: Path, extra: str = ''):
    """stdout 末行:V1.3 §HTML 交付协议 - Agent 必须 send 给用户"""
    extra_part = f' | {extra}' if extra else ''
    print(f"⚠️ ACTION=SEND_TO_USER | HTML={output_path.absolute()}{extra_part}")


def main():
    p = argparse.ArgumentParser(description='渲染身材照 GIF planner HTML(v2.3.1 · 兼任 gallery)')
    p.add_argument('--ids', help='逗号分隔的照片 ID(从外部带入)。与 --tag 二选一')
    p.add_argument('--tag', help='按 tag 拉所有照片(独立运行模式,无需先经 gallery)')
    p.add_argument('--tags', help='逗号分隔的 tag(用于输出文件名)')
    p.add_argument('--no-validate-files', action='store_true',
                   help='不跳过 DB 有但文件不存在的照片(默认跳过,validate_files=True)')
    p.add_argument('--no-embed-images', action='store_true',
                   help='不嵌图片为 base64(默认嵌)— 不嵌时走 file:// 路径,只能本地 Chrome 看')
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
    result = render(ids, out_path,
                    validate_files=not args.no_validate_files,
                    embed_images=not args.no_embed_images)
    n_avail = len(ids) - (1 if not args.no_validate_files else 0)  # 简化,实际数据可从 render 返回
    print(f"✓ 已生成: {result}")
    # V1.3 §HTML 交付协议:stdout 末行强制 send 协议
    emit_send_protocol(result)


if __name__ == '__main__':
    main()