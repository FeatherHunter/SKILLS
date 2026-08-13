#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_exercise_recap.py — 运动复盘 HTML(结果型 · E5)

对应 SKILL.md 唤醒词(5 个):
  - 运动复盘（本周）     → --period week
  - 运动复盘（本月）     → --period month
  - 运动复盘（最近 90 天）→ --period 90d
  - 运动复盘（今年）     → --period year
  - 运动复盘（自定义时间）→ --period range --from <F> --to <T>
对应模板: templates/exercise_recap.html

呈现数据(权威清单 §4):KPI(总时长/总消耗/运动频次/类型)+ 趋势小图 + 高频运动。
"""

from _base_render import render_template, write_html  # noqa: E402
COMMAND_CN = '运动复盘'
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'exercise_recap.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_scene_path  # noqa
from render_crud_view import _chain_valid, _quote_arg  # noqa
from exercise_tracker import resolve_window  # noqa

_PERIODS = {
    'week': ('本周', 'week'),
    'month': ('本月', 'month'),
    '90d': ('最近 90 天', None),
    'year': ('今年', None),
    'range': ('自定义时间', None),
}


def _range_for(period: str, from_date=None, to_date=None):
    if period == '90d':
        return resolve_window(None, days=90)
    if period == 'year':
        today = date.today()
        return f'{today.year}-01-01', today.isoformat()
    if period == 'range':
        return from_date or '2000-01-01', to_date or date.today().isoformat()
    return resolve_window(period)


def build_data(period: str, from_date=None, to_date=None):
    from db import find_db_path
    import sqlite3
    label, _ = _PERIODS[period]
    start, end = _range_for(period, from_date, to_date)
    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT date, exercise_type, category, duration_minutes, calories_burned "
        "FROM exercise_log WHERE date BETWEEN ? AND ? AND COALESCE(is_deleted, 0) = 0 "
        "ORDER BY date ASC",
        (start, end)).fetchall()
    conn.close()

    total_min = sum(r['duration_minutes'] or 0 for r in rows)
    total_cal = round(sum(r['calories_burned'] or 0 for r in rows), 1)
    active_days = len(set(r['date'] for r in rows))
    span_days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1

    cat_map = {'力量': '力量', '有氧': '有氧', '柔韧': '柔韧', '日常': '日常'}
    by_cat: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for r in rows:
        c = cat_map.get(r['category'], '未分类')
        by_cat[c] = by_cat.get(c, 0) + 1
        by_type[r['exercise_type']] = by_type.get(r['exercise_type'], 0) + 1

    cat_items = sorted(by_cat.items(), key=lambda kv: -kv[1])
    top_movements = [{'name': k, 'count': v} for k, v in sorted(by_type.items(), key=lambda kv: -kv[1])[:5]]

    # 趋势小图(按日消耗)
    by_date = {}
    for r in rows:
        by_date[r['date']] = by_date.get(r['date'], 0) + (r['calories_burned'] or 0)
    trend = [{'date': d, 'calories': v} for d, v in sorted(by_date.items())]

    summary = (f'{label}运动复盘:共 {len(rows)} 次运动 / {active_days} 天 / '
               f'{total_min} 分钟 / {total_cal:,.0f} 卡')
    if by_type:
        top = max(by_type, key=by_type.get)
        summary += f';最常做:{top}({by_type[top]} 次)'

    return {
        'status': 'ok',
        'data': {
            'summary': {
                'subtitle': f'{start} ~ {end} · {label}',
                'k1': {'label': '总时长', 'value': f'{total_min} 分钟',
                       'extra': f'{active_days}/{span_days} 天运动'},
                'k2': {'label': '总消耗', 'value': f'{total_cal:,.0f} 卡',
                       'extra': f'日均 {round(total_cal / max(1, span_days))}'},
                'k3': {'label': '运动频次', 'value': f'{len(rows)} 次',
                       'extra': f'平均 {round(len(rows) / max(1, active_days), 1)} 次/运动日'},
                'k4': {'label': '类型分布', 'value': f'{len(by_cat)} 类',
                       'extra': '、'.join(f'{c} {n}次' for c, n in cat_items[:3]) or '无'},
            },
            'cat_items': [{'name': c, 'count': n} for c, n in cat_items],
            'top_movements': top_movements,
            'trend': trend,
            'one_line': summary,
            'meta': {'start': start, 'end': end, 'period': period, 'label': label,
                     'today': date.today().isoformat()},
        },
        'message': f'已生成{label}运动复盘',
    }


def render_html(data):
    return render_template(TEMPLATE_PATH, data, COMMAND_CN)


def main():
    p = argparse.ArgumentParser(description='渲染运动复盘 HTML')
    p.add_argument('--period', choices=['week', 'month', '90d', 'year', 'range'], required=True)
    p.add_argument('--from', dest='from_date')
    p.add_argument('--to', dest='to_date')
    p.add_argument('--chain', help='AI 思考链(必填·强制规则 · 2026-08-02)')
    p.add_argument('--output')
    args = p.parse_args()
    if not _chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        print('   未传 = AI 未按 SKILL.md 流程执行,行为不可控。', file=sys.stderr)
        return 2
    label, _ = _PERIODS[args.period]
    scene = f'运动复盘（{label}）' if args.period != 'range' else '运动复盘（自定义时间）'
    try:
        data = build_data(args.period, args.from_date, args.to_date)
        data['data']['meta']['chain'] = args.chain.strip()
        data['data']['meta']['wake_word'] = scene
        argv = sys.argv[1:]
        if '--output' in argv:
            i = argv.index('--output')
            argv = argv[:i] + argv[i + 2:] if i + 1 < len(argv) else argv[:i]
        data['data']['meta']['render_cmd'] = f"python scripts/{Path(__file__).name} " + ' '.join(
            _quote_arg(a) for a in argv)
        data['data']['meta']['source'] = 'exercise_log (只读复盘)'
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, scene, 'result')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_html(html, out_path)
    print(f'✅ {out_path}')
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
