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


def embed_photo_as_base64(photo: dict, photos_dir: Path, max_dim: int = 500) -> dict:
    """读取图片 → 缩放(保持比例) → 转 base64 JPEG → 写回 photo

    2026-07-25 减体积:max_dim 800→500, quality 85→75。
    为何需要:Flybook / IM / 任何外部环境打开 HTML 时,相对路径的 <img> 会 broken。
    嵌入 base64 后 HTML 完全自包含。

    关键设计:base64 **只**用于静态 <img src="data:..."> 渲染,
    不放进 window.__DATA__(避免飞书 webview 审查 <script> 段截断 base64)。
    即使 JS 失败,HTML 解析阶段的 <img> 已经能显示图。
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
        # 转 JPEG base64(q75, 体积比 q85 小 ~30%)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=75, optimize=True)
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


def render(ids: list, output_path: Path, validate_files: bool = True, embed_images: bool = True, tag_from_args: str = '') -> Path:
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

    # v2.3.5(2026-07-25 适配用户新模板):
    # 用户重写模板后 JS 用 D.data.all_photos / p.photo_data_base64(原 v1.0 模式),
    # 这里恢复字段名,base64 放进 __DATA__。
    # 飞书 webview 审查会截断 <script> 段里的 base64 → JS 早 return 清空 photoList,
    # 飞书里看不到图(只 Chrome 正常)。这是用户明确接受的降级。
    embed = embed_images
    if embed:
        selected_for_display = [embed_photo_as_base64(p, photos_dir) for p in selected_for_display]
        all_photos_for_display = []
        for p in all_photos:
            if (photos_dir / p['photo_path']).exists():
                all_photos_for_display.append(embed_photo_as_base64(p, photos_dir))
    else:
        selected_for_display = list(selected_for_display)
        all_photos_for_display = [p for p in all_photos if (photos_dir / p['photo_path']).exists()]

    # v2.3.5:字段名改回 v1.0 风格(适配用户重写的 JS .all_photos / .selected_photos)
    # 但 all_photos 去掉 base64 字段(只 metadata,12 张全列但不嵌图,减小体积)
    # selected_photos 保留 base64(用户 JS 读 photo_data_base64 渲染 <img>)
    payload = {
        "status": "ok",
        "data": {
            "fetched_at": datetime.now().isoformat(timespec='seconds'),
            "selected_ids": [p['id'] for p in selected_for_display],
            "selected_photos": selected_for_display,  # 含 base64(用户 JS 渲染 <img>)
            "all_photos": [_meta_only(p) for p in all_photos_for_display],  # 仅 metadata,体积小
            "missing_ids": missing_ids,
            "missing_count": len(missing_ids),
            "embedded": embed,
            "current_tag": tag_from_args or '',
        },
        "message": f"身材照 GIF planner · 共 {len(selected_for_display)} 张可用 · 跳过 {len(missing_ids)} 张丢失" + (" · 📦 图片已嵌 base64" if embed else ""),
    }

    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    inject_data = f'<script>window.__DATA__ = {json.dumps(payload, ensure_ascii=False)};</script>'
    html = template.replace('<!--INJECT-DATA-->', inject_data)

    # v2.3.6(2026-07-25):预填 <!-- 动态生成 --> 为带 base64 <img> 的 photo-item HTML
    # 飞书 webview 审查会截断 <script>__DATA__</script> 段,用户 JS 早 return 但不清空 photoList
    # 浏览器解析阶段 <img> 已经渲染好,飞书里能看图
    # Chrome 里 JS 成功时,renderList() 整段 innerHTML 覆盖,会清空预填但用 __DATA__ 里的 base64 重画(正常)
    photo_list_html = _render_photo_list_html(selected_for_display)
    if '<!-- 动态生成 -->' in html:
        html = html.replace('<!-- 动态生成 -->', photo_list_html)
    else:
        # 兼容旧版占位符
        html = html.replace('<!--PHOTO_LIST-->', photo_list_html)

    output_path.write_text(html, encoding='utf-8')
    return output_path


def _meta_only(photo: dict) -> dict:
    """从 photo dict 抽 metadata,去掉 photo_data_base64(减小 __DATA__ 体积)"""
    return {
        'id': photo['id'],
        'date': photo['date'],
        'time': photo.get('time', ''),
        'tag': photo['tag'],
        'note': photo.get('note', ''),
        'photo_path': photo['photo_path'],
    }


def _render_photo_list_html(photos: list) -> str:
    """生成 photo-list 的静态 HTML(每项含 <img src="data:...">)

    关键:即使 __DATA__ 被飞书 webview 截断,这段 HTML 是浏览器解析阶段就渲染的,
    <img> 标签的 base64 src 不会被 JS 模板字符串拼接,直接用浏览器原生支持。
    """
    import html as html_mod
    items = []
    for idx, p in enumerate(photos, 1):
        b64 = p.get('photo_data_base64', '')
        # 无 base64 时降级:不渲染 <img>(避免 broken 图标,改成占位)
        if b64:
            img_tag = f'<img src="{b64}" alt="{html_mod.escape(p["tag"])}" loading="lazy">'
        else:
            img_tag = f'<div class="broken">📷<br>无图</div>'
        info_meta = f'#{p["id"]} · {p.get("time", "")}'
        note_safe = html_mod.escape(p.get('note', '') or '(无备注)')
        items.append(f'''
        <div class="photo-item" data-id="{p['id']}">
          <div class="sel-check">
            <input type="checkbox" class="sel-cb" data-id="{p['id']}" checked>
          </div>
          <div class="thumb">{img_tag}</div>
          <div class="info">
            <div><strong>{idx}.</strong> {html_mod.escape(p["tag"])} · {p["date"]}</div>
            <div class="meta">{info_meta}</div>
            <div class="crop-info none">未裁剪</div>
            <div class="note-line" style="font-size:11px; color:var(--fg3); margin-top:4px;">{note_safe}</div>
          </div>
          <div class="actions">
            <button class="move-up">↑ 上移</button>
            <button class="move-down">↓ 下移</button>
            <button class="crop-btn" data-id="{p['id']}">✂️ 框选裁剪</button>
            <button class="remove-btn" data-id="{p['id']}">✕ 移除</button>
          </div>
        </div>
        ''')
    return '\n'.join(items)


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
    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, f'身材照GIF规划器_{suffix}')
    result = render(ids, out_path,
                    validate_files=not args.no_validate_files,
                    embed_images=not args.no_embed_images,
                    tag_from_args=args.tag or '')
    n_avail = len(ids) - (1 if not args.no_validate_files else 0)  # 简化,实际数据可从 render 返回
    print(f"✓ 已生成: {result}")
    # V1.3 §HTML 交付协议:stdout 末行强制 send 协议
    emit_send_protocol(result)


if __name__ == '__main__':
    main()