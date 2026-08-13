#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_body_photo_gif_result.py — 生成身材照 GIF 结果 HTML 渲染器(结果型 · ticket #10)

对应 SKILL.md 唤醒词:生成身材照GIF
对应模板: templates/body_photo_gif_result.html

呈现数据(§9 P3):GIF 文件/时间跨度/帧数/合成照片总数/首末日期。
设计(对齐 #8 经验):
  - 内部调用 body_photo_tracker.generate_gif(写 GIF 文件)+ 组装结果 HTML
  - GIF 以 base64 内嵌(浏览器可播放动画 GIF;飞书友好降级为文件路径)
  - --chain 强制(R3);复制数据/复制日志(R2)
用法:
    python scripts/render_body_photo_gif_result.py --tag 正面 --days 90 --chain "1.识别→2.选照片→3.合成→4.渲染"
    python scripts/render_body_photo_gif_result.py --tag 正面 --start 2026-01-01 --end 2026-06-30 --chain "..."
    python scripts/render_body_photo_gif_result.py --tag 正面 --photo-id 12 --photo-id 22 --chain "..."
"""

from _base_render import render_template, write_html  # noqa: E402
COMMAND_CN = '生成身材照GIF'
import argparse
import base64
import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'body_photo_gif_result.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_scene_path  # noqa
from render_crud_view import _chain_valid, _quote_arg  # noqa


def build(tag, start=None, end=None, days=None, photo_ids=None,
          width=400, height=600, duration=500, transition='cut'):
    import body_photo_tracker as bpt
    import db as db_mod
    db_mod.init_db(str(db_mod.find_db_path(SKILL_DIR, "calorie_data.db")))  # 幂等自愈(2026-08-02)

    gif_path = bpt.generate_gif(
        tag=tag, start_date=start, end_date=end, days=days, photo_ids=photo_ids,
        width=width, height=height, duration=duration, transition=transition,
    )
    if not gif_path:
        raise ValueError('GIF 生成失败(检查标签/日期范围/照片文件)')

    # 合成照片信息(与 GIF 相同过滤条件)
    rows = bpt.list_photos(days=days or 36500, tag=tag,
                           date_from=start, date_to=end, limit=100000)
    if photo_ids:
        rows = [r for r in rows if r[0] in photo_ids]
    dates = sorted(r[1] for r in rows)
    first_date, last_date = (dates[0], dates[-1]) if dates else (None, None)

    # C3(2026-08-02):帧数/照片总数从 generate_gif 模块属性读取(呈现数据承诺字段)
    info = bpt.get_last_gif_info()
    photo_count = info.get('photo_count', len(rows))
    frame_count = info.get('frame_count')

    # GIF base64 内嵌(浏览器可播放;体积大时前端降级路径)
    gif_b64 = None
    try:
        data = gif_path.read_bytes()
        if len(data) < 8 * 1024 * 1024:
            gif_b64 = f"data:image/gif;base64,{base64.b64encode(data).decode('ascii')}"
    except Exception:
        pass

    return {
        'status': 'ok',
        'data': {
            'scene': '生成身材照 GIF',
            'gif': {
                'path': str(gif_path),
                'file_name': gif_path.name,
                'gif_data_base64': gif_b64,
                'tag': tag,
                'start_date': start or (dates[0] if dates else None),
                'end_date': end or (dates[-1] if dates else None),
                'photo_count': photo_count,
                'frame_count': frame_count,
                'first_date': first_date,
                'last_date': last_date,
                'width': width, 'height': height,
                'duration_ms': duration,
                'transition': transition,
            },
            'meta': {
                'action_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'entity_type': '生成身材照 GIF', 'wake_word': '生成身材照GIF',
                'source': 'body_photos + GIF 合成 (写文件)',
            },
        },
        'message': f'生成身材照 GIF · {len(rows)} 张照片合成',
    }


def render_html(data):
    return render_template(TEMPLATE_PATH, data, COMMAND_CN)


def emit_send_protocol(output_path):
    print(f"⚠️ ACTION=SEND_TO_USER | HTML={output_path.absolute()}")


def main():
    p = argparse.ArgumentParser(description='渲染生成身材照 GIF 结果 HTML')
    p.add_argument('--tag', required=True, help='照片标签(包含匹配)')
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--start', help='开始日期 YYYY-MM-DD(与 --end 成对)')
    g.add_argument('--days', type=int, help='最近 N 天')
    g.add_argument('--photo-id', type=int, action='append', help='显式照片 ID(可重复)')
    p.add_argument('--end', help='结束日期 YYYY-MM-DD')
    p.add_argument('--width', type=int, default=400)
    p.add_argument('--height', type=int, default=600)
    p.add_argument('--duration', type=int, default=500, help='单帧 ms')
    p.add_argument('--transition', choices=['cut', 'fade', 'dissolve'], default='cut')
    p.add_argument('--chain', help='AI 思考链(必填·强制规则 · 2026-08-02)')
    p.add_argument('--output')
    args = p.parse_args()

    if not _chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        print('   请传入你的实际处理步骤,例如: --chain "1.识别唤醒词→2.选照片→3.合成GIF→4.渲染HTML"', file=sys.stderr)
        return 2
    if args.start and not args.end:
        print('❌ --start 需要与 --end 成对使用', file=sys.stderr)
        return 1

    try:
        data = build(args.tag, start=args.start, end=args.end, days=args.days,
                     photo_ids=args.photo_id, width=args.width, height=args.height,
                     duration=args.duration, transition=args.transition)
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

    out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, '生成身材照 GIF', 'result')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_html(html, out_path)
    print(f'✅ {out_path}')
    print(f'   GIF: {data["data"]["gif"]["path"]}')
    emit_send_protocol(out_path)
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
