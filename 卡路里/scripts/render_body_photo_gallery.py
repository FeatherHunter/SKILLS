#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_body_photo_gallery.py — 看身材照 HTML 渲染器(结果型 · ticket #10)

对应 SKILL.md 唤醒词:查身材照
对应模板: templates/body_photo_gallery.html

呈现数据(§9 P2):照片网格 + 时间/标签筛选 + 照片总数/标签计数 + 距上次拍照天数。
设计(对齐 #8 经验):
  - 与 gif_planner 分离:本页 = 轻量浏览(gallery),gif_planner = GIF 规划
  - --chain 强制(R3)
  - 缩略图 base64 内嵌(飞书友好)+ 复制数据/复制日志(R2)
用法:
    python scripts/render_body_photo_gallery.py --chain "1.识别→2.读DB→3.渲染"
    python scripts/render_body_photo_gallery.py --days 30 --chain "..."
    python scripts/render_body_photo_gallery.py --start 2026-07-01 --end 2026-07-31 --chain "..."
    python scripts/render_body_photo_gallery.py --start 2026-07-15 --tag 正面 --chain "..."
时间参数一统(2026-08-02 用户拍板):--days N(最近 N 天)/ --start --end(范围)
/ --start 单日(此时 end 自动 = start)三种表达都归一为 start/end 传给查询。
"""

from _base_render import render_template, write_html  # noqa: E402
COMMAND_CN = '查身材照'
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'body_photo_gallery.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_scene_path  # noqa
from render_crud_view import _chain_valid, _quote_arg  # noqa
from render_body_photo_gif_planner import embed_photo_as_base64  # noqa


def list_all_photos(date_from=None, date_to=None, limit=500):
    """取照片元数据(按日期倒序);文件缺失项标注,供前端降级显示"""
    import db as db_mod
    db_path = db_mod.find_db_path(SKILL_DIR, "calorie_data.db")
    db_mod.init_db(str(db_path))  # 幂等:新环境缺表时自愈(2026-08-02 第 4 层审查)
    where, params = [], []
    if date_from:
        where.append('date >= ?'); params.append(date_from)
    if date_to:
        where.append('date <= ?'); params.append(date_to)
    sql = f"SELECT id, date, time, photo_path, tag, note FROM body_photos"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY date DESC, time DESC LIMIT ?"
    params.append(limit)
    with db_mod.connection(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(zip(['id', 'date', 'time', 'photo_path', 'tag', 'note'], r)) for r in rows]


# 飞书单消息体积上限的保守预算:HTML 全文件 ≤ 4MB(issue #51 · 2026-08-09)
# 原因:身材照数量多时,base64 全量内嵌会让 HTML 超出飞书发送限制 → 核心场景(查身材照)断在最后一步。
# 方案:嵌入累计超预算 → 剩余照片标 embed_skipped,前端显示"未嵌入(体积超限)"而非 broken;
# 配合模板提示按时间/标签筛选查看,保证「能发出去」永远优先于「一次看全」。
MAX_EMBED_BYTES = 4 * 1024 * 1024


def build(date_from, date_to, tag_filter, limit=500, embed=True, max_embed_bytes=MAX_EMBED_BYTES):
    """组装看身材照 result 数据契约

    2026-08-09 体积预算(issue #51 Bug 2):embed 累计超过 max_embed_bytes 后,
    剩余照片不再内嵌(标 embed_skipped),保证 HTML 体积可控、飞书可发。
    """
    import body_photo_tracker as bpt
    photos = list_all_photos(date_from, date_to, limit)

    # 标签过滤(多标签包含匹配)
    if tag_filter:
        photos = [p for p in photos if bpt.tags_contain(p['tag'], tag_filter)]

    # 文件存在性 + 缩略图(缺文件 → 标 broken)
    photos_dir = None
    try:
        photos_dir = bpt.get_photos_dir()
    except SystemExit:
        photos_dir = None
    embed_budget = max_embed_bytes
    skipped_embeds = 0
    for i, p in enumerate(photos):
        p['tag_list'] = bpt.parse_tags(p['tag'])
        if photos_dir:
            p['file_exists'] = (photos_dir / p['photo_path']).exists()
            if p['file_exists'] and embed:
                if embed_budget > 0:
                    photo = embed_photo_as_base64(p, photos_dir, max_dim=500)
                    embedded_size = len(photo.get('photo_data_base64', ''))
                    if photo.get('photo_data_base64'):
                        embed_budget -= embedded_size
                        photos[i] = photo
                    else:
                        # 文件存在但嵌入失败(读图/转码异常)→ 也按缺失处理
                        p['embed_error'] = True
                else:
                    # 体积预算耗尽 → 标跳过,前端显示"未嵌入"而非 broken
                    p['embed_skipped'] = True
                    skipped_embeds += 1

    # 标签计数(全量,不受筛选影响 → 前端展示"该标签有几张")
    tag_counts = {}
    for p in list_all_photos(None, None, 5000):
        for t in bpt.parse_tags(p['tag']):
            tag_counts[t] = tag_counts.get(t, 0) + 1

    # 距上次拍照天数(最近一张照片距今)
    days_since_last = None
    if photos:
        from datetime import date as _date
        days_since_last = (_date.today() - _date.fromisoformat(photos[0]['date'])).days

    return {
        'status': 'ok',
        'data': {
            'scene': '看身材照',
            'filters': {'tag': tag_filter or '', 'date_from': date_from or '', 'date_to': date_to or ''},
            'total_count': len(photos),
            'tag_counts': [{'tag': k, 'count': v} for k, v in sorted(tag_counts.items())],
            'days_since_last': days_since_last,
            'photos': photos,
            'meta': {
                'action_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'entity_type': '看身材照', 'wake_word': '查身材照',
                'source': 'body_photos (只读)',
                'embed_budget_bytes': max_embed_bytes,
                'embed_skipped_count': skipped_embeds,
            },
        },
        'message': f'看身材照 · {len(photos)} 张',
    }


def render_html(data):
    return render_template(TEMPLATE_PATH, data, COMMAND_CN)


def emit_send_protocol(output_path):
    print(f"⚠️ ACTION=SEND_TO_USER | HTML={output_path.absolute()}")


def main():
    p = argparse.ArgumentParser(description='渲染看身材照 gallery HTML')
    p.add_argument('--tag', help='按标签筛选(包含匹配)')
    g = p.add_mutually_exclusive_group()
    g.add_argument('--start', help='起始日期 YYYY-MM-DD(单日时 end 自动 = start)')
    g.add_argument('--days', type=int, help='最近 N 天(默认 90)')
    p.add_argument('--end', help='结束日期 YYYY-MM-DD')
    p.add_argument('--limit', type=int, default=500, help='最多返回张数')
    p.add_argument('--no-embed-images', action='store_true', help='不嵌 base64')
    p.add_argument('--chain', help='AI 思考链(必填·强制规则 · 2026-08-02)')
    p.add_argument('--output')
    args = p.parse_args()

    if not _chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        print('   请传入你的实际处理步骤,例如: --chain "1.识别唤醒词→2.调CLI读DB→3.渲染HTML"', file=sys.stderr)
        return 2

    # 时间参数归一:--days / --start(单日=start+end) / --start+--end → (start, end)
    from datetime import date as _date, timedelta as _td
    start, end = args.start, args.end
    if start and not end:
        end = start
    if not start and not end:
        days = args.days if args.days else 90
        end = _date.today().isoformat()
        start = (_date.today() - _td(days=days - 1)).isoformat()

    try:
        data = build(start, end, args.tag, args.limit, embed=not args.no_embed_images)
        data['data']['meta']['chain'] = args.chain.strip()
        argv = sys.argv[1:]
        if '--output' in argv:
            i = argv.index('--output')
            argv = argv[:i] + argv[i + 2:] if i + 1 < len(argv) else argv[:i]
        data['data']['meta']['render_cmd'] = (
            f"python scripts/{Path(__file__).name} " + ' '.join(_quote_arg(a) for a in argv))
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, '看身材照', 'result')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_html(html, out_path)
    print(f'✅ {out_path}')
    print(f'   照片: {data["data"]["total_count"]} 张')
    emit_send_protocol(out_path)
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
