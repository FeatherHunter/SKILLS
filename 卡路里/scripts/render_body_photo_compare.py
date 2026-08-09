#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_body_photo_compare.py — 对比两张照片 HTML 渲染器(结果型 · ticket #10)

对应 SKILL.md 唤醒词:对比两张照片
对应模板: templates/body_photo_compare.html

呈现数据(§9 P3):照片 1+2 并排 + 日期标注 + 间隔天数 + 各自标签/备注。
设计(对齐 #8 经验):
  - --chain 强制(R3);base64 内嵌(飞书友好);复制数据/复制日志(R2)
用法:
    python scripts/render_body_photo_compare.py --id1 12 --id2 22 --chain "1.识别→2.读DB→3.渲染"
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'body_photo_compare.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_scene_path  # noqa
from render_crud_view import _chain_valid, _quote_arg  # noqa
from render_body_photo_gif_planner import embed_photo_as_base64  # noqa


def build(id1, id2, embed=True):
    import body_photo_tracker as bpt
    import db as db_mod
    db_mod.init_db(str(db_mod.find_db_path(SKILL_DIR, "calorie_data.db")))  # 幂等自愈(2026-08-02)
    p1 = bpt.get_photo_row(id1)
    if not p1:
        raise ValueError(f"照片 #{id1} 不存在")
    p2 = bpt.get_photo_row(id2)
    if not p2:
        raise ValueError(f"照片 #{id2} 不存在")
    if id1 == id2:
        raise ValueError("对比的两张照片不能是同一张")

    for p in (p1, p2):
        p['tag_list'] = bpt.parse_tags(p['tag'])

    from datetime import date as _date
    interval = (_date.fromisoformat(p2['date']) - _date.fromisoformat(p1['date'])).days
    interval = abs(interval)

    # 跨标签对比警告(2026-08-03 验收拍板 · 方案 B:警告不拦截)
    # 同标签 = 同角度同姿势,对比才有可比性;不同标签仅提示,不阻止渲染
    cross_tag = sorted(p1['tag_list']) != sorted(p2['tag_list'])

    try:
        photos_dir = bpt.get_photos_dir()
        if embed:
            p1 = embed_photo_as_base64(p1, photos_dir, max_dim=800)
            p2 = embed_photo_as_base64(p2, photos_dir, max_dim=800)
    except SystemExit:
        pass

    return {
        'status': 'ok',
        'data': {
            'scene': '对比两张照片',
            'photo1': p1, 'photo2': p2,
            'interval_days': interval,
            'order_by_date': p1['date'] <= p2['date'],
            'cross_tag_warning': cross_tag,
            'meta': {
                'action_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'entity_type': '对比两张照片', 'wake_word': '对比两张照片',
                'source': 'body_photos (只读)',
            },
        },
        'message': f'对比照片 #{id1} vs #{id2} · 间隔 {interval} 天',
    }


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


def emit_send_protocol(output_path):
    print(f"⚠️ ACTION=SEND_TO_USER | HTML={output_path.absolute()}")


def main():
    p = argparse.ArgumentParser(description='渲染对比两张身材照 HTML')
    p.add_argument('--id1', type=int, required=True, help='照片 1 ID')
    p.add_argument('--id2', type=int, required=True, help='照片 2 ID')
    p.add_argument('--no-embed-images', action='store_true', help='不嵌 base64')
    p.add_argument('--chain', help='AI 思考链(必填·强制规则 · 2026-08-02)')
    p.add_argument('--output')
    args = p.parse_args()

    if not _chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        print('   请传入你的实际处理步骤,例如: --chain "1.识别唤醒词→2.调CLI读DB→3.渲染HTML"', file=sys.stderr)
        return 2

    try:
        data = build(args.id1, args.id2, embed=not args.no_embed_images)
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

    out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, '对比两张照片', 'result')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    print(f'✅ {out_path}')
    print(f'   间隔: {data["data"]["interval_days"]} 天')
    if data['data'].get('cross_tag_warning'):
        tags1 = ','.join(data['data']['photo1']['tag_list'] or ['(无)'])
        tags2 = ','.join(data['data']['photo2']['tag_list'] or ['(无)'])
        print(f'⚠️ 跨标签对比警告:照片 #{args.id1} 标签[{tags1}] vs #{args.id2} 标签[{tags2}] — 非同标签对比,可比性较弱,建议同角度照片对比')
    emit_send_protocol(out_path)
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
