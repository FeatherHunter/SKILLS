#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_exercise_cardio.py — 有氧训练总览 HTML(结果型 · E4.3)

对应 SKILL.md 唤醒词:看有氧训练总览
对应模板: templates/exercise_cardio.html

呈现数据(权威清单 §4):按类型聚合的表(次数/总时长/总距离/平均配速)。
配速 = 时长(min) / 距离(km)(距离缺失不计算)。
"""

from _base_render import render_template, write_html  # noqa: E402
COMMAND_CN = '看有氧训练总览'
import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'exercise_cardio.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_scene_path  # noqa
from render_crud_view import _chain_valid, _quote_arg  # noqa


def build_data(days: int = 90):
    from db import find_db_path
    import sqlite3
    from datetime import date, timedelta
    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    start = (date.today() - timedelta(days=days - 1)).isoformat()
    rows = conn.execute(
        "SELECT exercise_type, duration_minutes, distance_km FROM exercise_log "
        "WHERE category = '有氧' AND date >= ? AND COALESCE(is_deleted, 0) = 0",
        (start,)).fetchall()
    conn.close()

    by_type: dict[str, dict] = {}
    for etype, minutes, dist in rows:
        t = by_type.setdefault(etype, {'count': 0, 'minutes': 0, 'distance': 0.0})
        t['count'] += 1
        t['minutes'] += minutes or 0
        t['distance'] += dist or 0.0

    items = []
    for name, t in sorted(by_type.items(), key=lambda kv: -kv[1]['count']):
        pace = round(t['minutes'] / t['distance'], 1) if t['distance'] else None
        items.append({'name': name, 'count': t['count'], 'minutes': t['minutes'],
                      'distance': round(t['distance'], 1), 'pace': pace})

    total_count = sum(i['count'] for i in items)
    total_min = sum(i['minutes'] for i in items)
    total_dist = round(sum(i['distance'] for i in items), 1)

    return {
        'status': 'ok',
        'data': {
            'summary': {
                'subtitle': f'最近 {days} 天 · {len(items)} 种有氧 · {total_count} 次',
                'k1': {'label': '总次数', 'value': str(total_count), 'extra': f'{days} 天内'},
                'k2': {'label': '总时长', 'value': f'{total_min} 分钟',
                       'extra': f'平均 {round(total_min / max(1, total_count))} 分/次'},
                'k3': {'label': '总距离', 'value': f'{total_dist} km',
                       'extra': f'{len([i for i in items if i["distance"]])} 种有距离'},
                'k4': {'label': '平均配速', 'value': _avg_pace(items),
                       'extra': '分钟/km(按距离加权)'},
                'table_header': ("<tr><th>类型</th><th class='num'>次数</th>"
                                 "<th class='num'>总时长</th><th class='num'>总距离</th>"
                                 "<th class='num'>平均配速</th></tr>"),
                'table_title': '按类型聚合',
            },
            'items': items,
            'meta': {'days': days, 'today': date.today().isoformat()},
        },
        'message': f'已生成有氧训练总览({len(items)} 种类型)',
    }


def _avg_pace(items):
    paced = [i for i in items if i['pace']]
    if not paced:
        return '—'
    dist_sum = sum(i['distance'] for i in paced)
    min_sum = sum(i['distance'] * i['pace'] for i in paced)
    return f'{round(min_sum / max(0.001, dist_sum), 1)} 分/km' if dist_sum else '—'


def render_html(data):
    return render_template(TEMPLATE_PATH, data, COMMAND_CN)


def main():
    p = argparse.ArgumentParser(description='渲染有氧训练总览 HTML')
    p.add_argument('--days', type=int, default=90)
    p.add_argument('--chain', help='AI 思考链(必填·强制规则 · 2026-08-02)')
    p.add_argument('--output')
    args = p.parse_args()
    if not _chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        print('   未传 = AI 未按 SKILL.md 流程执行,行为不可控。', file=sys.stderr)
        return 2
    try:
        data = build_data(args.days)
        data['data']['meta'] = {'chain': args.chain.strip(), 'wake_word': '看有氧训练总览'}
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, '看有氧训练总览', 'result')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_html(html, out_path)
    print(f'✅ {out_path}')
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
