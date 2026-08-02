#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_exercise_trend.py — 运动趋势 HTML(结果型 · E4.4)

对应 SKILL.md 唤醒词:看运动趋势
对应模板: templates/exercise_trend.html

呈现数据(权威清单 §4):折线(每日时长/每日消耗/每周频次)+ 汇总。
默认最近 30 天(--days 可调)。
"""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'exercise_trend.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_scene_path  # noqa
from render_crud_view import _chain_valid, _quote_arg  # noqa


def build_data(days: int = 30):
    from db import find_db_path
    import sqlite3
    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    start = (date.today() - timedelta(days=days - 1)).isoformat()
    end = date.today().isoformat()
    rows = conn.execute(
        "SELECT date, duration_minutes, calories_burned FROM exercise_log "
        "WHERE date BETWEEN ? AND ? AND COALESCE(is_deleted, 0) = 0 "
        "ORDER BY date ASC",
        (start, end)).fetchall()
    conn.close()

    by_date: dict[str, dict] = {}
    for d, minutes, cal in rows:
        day = by_date.setdefault(d, {'minutes': 0, 'calories': 0, 'count': 0})
        day['minutes'] += minutes or 0
        day['calories'] += cal or 0
        day['count'] += 1

    # 每日序列(补零)
    daily = []
    for i in range(days):
        d = (date.fromisoformat(start) + timedelta(days=i)).isoformat()
        day = by_date.get(d, {'minutes': 0, 'calories': 0, 'count': 0})
        daily.append({'date': d, 'minutes': day['minutes'], 'calories': day['calories'],
                      'count': day['count']})

    # 每周频次(ISO 周)
    from datetime import datetime
    week_map: dict[str, int] = {}
    for d, day in by_date.items():
        iso = datetime.fromisoformat(d).isocalendar()
        key = f'{iso[0]}-W{iso[1]:02d}'
        week_map[key] = week_map.get(key, 0) + day['count']
    weekly = [{'label': k, 'count': v} for k, v in sorted(week_map.items())]

    total_min = sum(x['minutes'] for x in daily)
    total_cal = sum(x['calories'] for x in daily)
    active = sum(1 for x in daily if x['count'])
    peak = max((x['calories'] for x in daily), default=0)

    return {
        'status': 'ok',
        'data': {
            'summary': {
                'subtitle': f'最近 {days} 天 · {active} 天运动 · 总 {total_cal:,} 卡',
                'k1': {'label': '运动天数', 'value': str(active), 'extra': f'占 {days} 天的 {round(active / days * 100)}%'},
                'k2': {'label': '总时长', 'value': f'{total_min} 分钟', 'extra': f'日均 {round(total_min / max(1, days))}'},
                'k3': {'label': '总消耗', 'value': f'{total_cal:,} 卡', 'extra': f'日均 {round(total_cal / max(1, days))}'},
                'k4': {'label': '峰值', 'value': f'{peak:,} 卡', 'extra': '单日最高消耗'},
            },
            'daily': daily,
            'weekly': weekly,
            'meta': {'start': start, 'end': end, 'days': days, 'today': end},
        },
        'message': f'已生成运动趋势({days} 天)',
    }


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


def main():
    p = argparse.ArgumentParser(description='渲染运动趋势 HTML')
    p.add_argument('--days', type=int, default=30)
    p.add_argument('--chain', help='AI 思考链(必填·强制规则 · 2026-08-02)')
    p.add_argument('--output')
    args = p.parse_args()
    if not _chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        print('   未传 = AI 未按 SKILL.md 流程执行,行为不可控。', file=sys.stderr)
        return 2
    try:
        data = build_data(args.days)
        data['data']['meta'] = {'chain': args.chain.strip(), 'wake_word': '看运动趋势'}
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, '看运动趋势', 'result')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    print(f'✅ {out_path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
