#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_meal_distribution.py — 餐别分布 HTML 渲染器(结果型)

对应 SKILL.md 唤醒词: 看早餐（最近 7 天）/ 看午餐（最近 7 天）/ 看晚餐（最近 7 天）/ 看加餐（最近 7 天）/ 看全部餐别分布（最近 7 天）
对应模板: templates/meal_distribution.html

呈现数据: 表 + 该餐别日均 + 一句话;全部 = 表 + 饼图 + 占比%
"""

from _base_render import render_template, write_html  # noqa: E402
COMMAND_CN = '看餐别分布'
import argparse, json, sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'meal_distribution.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa

# 4 类餐别时间窗(与 render_today_diet / diet.infer_meal_type 折叠口径一致)
MEAL_WINDOWS = {
    'breakfast': (5, 10),   # 早餐 5-10
    'lunch': (11, 14),      # 午餐 11-14
    'dinner': (17, 21),     # 晚餐 17-21
    'snack': (14, 17, 21, 24),  # 加餐 = 下午茶 14-17 + 夜宵 21-24(与 4 类折叠一致)
}
MEAL_LABELS = {'breakfast': '早餐', 'lunch': '午餐', 'dinner': '晚餐', 'snack': '加餐'}


def _in_window(hour, win):
    if len(win) == 2:
        lo, hi = win
        return lo <= hour < hi
    lo1, hi1, lo2, hi2 = win
    return (lo1 <= hour < hi1) or (lo2 <= hour < hi2)


def build_data(days, meal):
    from db import find_db_path
    import sqlite3
    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    end = date.today()
    start = end - timedelta(days=days - 1)
    cur.execute('''
        SELECT date, time, food_name, grams, calories, protein, carbs, fat
        FROM food_log WHERE date BETWEEN ? AND ? AND food_name != '💧水'
        ORDER BY date, time
    ''', (start.isoformat(), end.isoformat()))
    rows = cur.fetchall()
    conn.close()

    items = []
    by_meal = {}
    for d, t, food, g, cal, pro, carb, fat in rows:
        try:
            hour = int(str(t).split(':')[0])
        except (ValueError, AttributeError):
            hour = -1
        m = None
        for key, win in MEAL_WINDOWS.items():
            if _in_window(hour, win):
                m = key
                break
        if m is None:
            m = 'snack'
        by_meal.setdefault(m, []).append(cal or 0)
        items.append({'date': d, 'time': (t or '')[ : 5], 'food': food, 'grams': g or 0,
                      'cal': round(float(cal or 0), 1), 'pro': float(pro or 0),
                      'carb': float(carb or 0), 'fat': float(fat or 0), 'meal': m})

    if meal == 'all':
        selected = items
        dist = [{'meal': key, 'label': MEAL_LABELS[key], 'count': len(v),
                 'cal': round(sum(v), 1)} for key, v in by_meal.items()]
        total_cal = sum(x['cal'] for x in dist) or 1
        for x in dist:
            x['pct'] = round(x['cal'] / total_cal * 100, 1)
        summary = {'days': days, 'total': len(selected),
                   'avg': round(sum(x['cal'] for x in selected) / max(1, days), 1),
                   'one_line': _all_line(dist)}
        view = 'all'
    else:
        selected = [x for x in items if x['meal'] == meal]
        label = MEAL_LABELS.get(meal, meal)
        total_cal = round(sum(x['cal'] for x in selected), 1)
        avg = round(total_cal / max(1, days), 1)
        summary = {'days': days, 'total': len(selected), 'total_cal': total_cal,
                   'avg': avg,
                   'one_line': f'最近 {days} 天{label}:{len(selected)} 餐,日均 {avg} 卡'}
        dist = []
        view = 'single'

    return {
        'status': 'ok',
        'data': {
            'summary': summary,
            'items': selected,
            'dist': dist,
            'view': view,
            'meal': meal,
            'meta': {'start': start.isoformat(), 'end': end.isoformat(), 'days': days,
                     'meal_label': MEAL_LABELS.get(meal, '全部餐别')},
        },
        'message': f'餐别分布 {start.isoformat()} ~ {end.isoformat()}',
    }


def _all_line(dist):
    if not dist:
        return '最近 7 天没有饮食记录'
    top = max(dist, key=lambda x: x['cal'])
    return f'最近 7 天共 {sum(x["count"] for x in dist)} 餐;{top["label"]}热量占比最高({top["pct"]}%)'


def render_html(data):
    return render_template(TEMPLATE_PATH, data, COMMAND_CN)


def main():
    p = argparse.ArgumentParser(description='渲染餐别分布 HTML(结果型 · 最近 N 天)')
    p.add_argument('--meal', choices=['breakfast', 'lunch', 'dinner', 'snack', 'all'], default='all')
    p.add_argument('--days', type=int, default=7)
    p.add_argument('--output')
    p.add_argument('--chain', help='AI 思考链注入(meta.chain,不进 UI;复制日志可带出 · R3)')
    args = p.parse_args()
    try:
        data = build_data(args.days, args.meal)
        if args.chain:
            data['data']['meta']['chain'] = args.chain
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, '餐别分布')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_html(html, out_path)
    sm = data['data']['summary']
    print(f'✅ {out_path}')
    print(f'   餐别: {args.meal} | {data["data"]["meta"]["start"]} ~ {data["data"]["meta"]["end"]} | {sm["total"]} 餐')
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
