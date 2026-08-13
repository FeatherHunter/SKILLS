#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_today_meals.py — 吃的记录 HTML 渲染器(报告型 · 详细列表)

对应 SKILL.md 唤醒词: 看本周饮食 / 看上周饮食 / 看本月饮食 / 看上月饮食 / 看最近 7 天饮食 / 看最近 30 天饮食 / 看某段时间饮食 / 看「有备注」的饮食记录
对应模板: templates/today_meals.html

v1.0 扩展(ticket #3):
  --week current|last   自然周(周一到周日)
  --month current|last  自然月
  --with-note           只看有备注的记录(看「有备注」的饮食记录)
"""

from _base_render import render_template, write_html  # noqa: E402
COMMAND_CN = '看饮食记录'
import argparse, json, sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'today_meals.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa


def _load_data(input_path):
    raw = json.loads(Path(input_path).read_text(encoding='utf-8'))
    if raw.get('status') != 'ok':
        raise ValueError('数据状态非 ok')
    return raw


def _natural_week(week: str) -> tuple[str, str]:
    """自然周(周一到周日)起止日期"""
    today = date.today()
    if week == 'last':
        today = today - timedelta(days=7)
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start.isoformat(), end.isoformat()


def _natural_month(month: str) -> tuple[str, str]:
    """自然月起止日期"""
    today = date.today()
    if month == 'last':
        first = today.replace(day=1) - timedelta(days=1)
        return first.replace(day=1).isoformat(), first.isoformat()
    start = today.replace(day=1)
    nxt = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    end = nxt - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def build_data(start, end, with_note=False):
    """从 food_log 取 [start,end] 区间所有食物记录"""
    from db import find_db_path
    import sqlite3
    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    note_cond = "AND note IS NOT NULL AND note != ''" if with_note else ''
    cur.execute(f'''
        SELECT date, time, food_name, grams, calories, protein, carbs, fat, note,
          CASE
            WHEN time IS NOT NULL AND CAST(strftime('%H', time) AS INT) BETWEEN 5 AND 10 THEN 'breakfast'
            WHEN time IS NOT NULL AND CAST(strftime('%H', time) AS INT) BETWEEN 11 AND 14 THEN 'lunch'
            WHEN time IS NOT NULL AND CAST(strftime('%H', time) AS INT) BETWEEN 17 AND 21 THEN 'dinner'
            ELSE 'snack'
          END AS meal_type
        FROM food_log
        WHERE date BETWEEN ? AND ? {note_cond}
        ORDER BY date DESC, time DESC
    ''', (start, end))
    items = []
    for row in cur.fetchall():
        d, t, fn, g, c, p, cb, f, note, mt = row
        items.append({
            'date': d, 'time': t or '—',
            'food_name': fn or '—',
            'meal_type': mt,
            'grams': float(g) if g else 0,
            'calorie': round(float(c) if c else 0, 1),
            'protein': float(p) if p else 0,
            'carb':  float(cb) if cb else 0,
            'fat':   float(f) if f else 0,
            'note': note or '',
        })
    conn.close()

    days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    total_cal = round(sum(float(i['calorie'] or 0) for i in items), 1)
    total_prot = sum(float(i['protein'] or 0) for i in items)
    total_carb = sum(float(i['carb'] or 0) for i in items)
    total_fat = sum(float(i['fat'] or 0) for i in items)
    water = sum(float(i['grams'] or 0) for i in items if (i['food_name'] or '') == '💧水')
    avg_cal = round(total_cal / max(1, days), 1)
    avg_water = round(water / max(1, days), 0)

    return {
        'status': 'ok',
        'data': {
            'summary': {
                'total_calorie': total_cal,
                'avg_calorie': avg_cal,
                'total_protein': total_prot,
                'total_carb': total_carb,
                'total_fat': total_fat,
                'protein_target': 120,
                'total_water': water,
                'avg_water': avg_water,
                'with_note': with_note,
                'note_count': sum(1 for i in items if i['note']),
            },
            'items': items,
            'meta': {'start': start, 'end': end, 'days': days, 'today': date.today().isoformat()},
        },
        'message': f'已生成吃的记录 ({start} ~ {end}, {len(items)} 条)',
    }


def render_html(data):
    return render_template(TEMPLATE_PATH, data, COMMAND_CN)


def main():
    p = argparse.ArgumentParser(description='渲染吃的记录 HTML(报告型 · 详细列表)')
    p.add_argument('--start')
    p.add_argument('--end')
    p.add_argument('--days', type=int, default=3)
    p.add_argument('--week', choices=['current', 'last'], help='自然周(周一到周日)')
    p.add_argument('--month', choices=['current', 'last'], help='自然月')
    p.add_argument('--with-note', action='store_true', help='只看有备注的记录')
    p.add_argument('--mock')
    p.add_argument('--output')
    p.add_argument('--chain', help='AI 思考链注入(meta.chain,不进 UI;复制日志可带出 · R3)')
    args = p.parse_args()
    if args.week:
        s, e = _natural_week(args.week)
        label = '本周' if args.week == 'current' else '上周'
    elif args.month:
        s, e = _natural_month(args.month)
        label = '本月' if args.month == 'current' else '上月'
    elif not args.start or not args.end:
        end_d = date.today()
        start_d = end_d - timedelta(days=args.days - 1)
        s, e = start_d.isoformat(), end_d.isoformat()
        label = f'最近 {args.days} 天'
    else:
        s, e = args.start, args.end
        label = '某段时间'
    try:
        data = _load_data(args.mock) if args.mock else build_data(s, e, with_note=args.with_note)
        # #44 审查:场景标签注入(标题动态:本周饮食/最近 7 天饮食…)+ 日均蛋白(呈现数据要求)
        data['data']['meta']['label'] = label
        if args.with_note:
            data['data']['meta']['label'] = '有备注的'
        data['data']['summary']['avg_protein'] = round(
            data['data']['summary']['total_protein'] / max(1, data['data']['meta']['days']), 1)
        if args.chain:
            data['data']['meta']['chain'] = args.chain
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, f'{label}饮食')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_html(html, out_path)
    sm = data['data']['summary']
    print(f'✅ {out_path}')
    print(f'   范围: {s} ~ {e} | 食物 {len(data["data"]["items"])} 条 | 总卡 {sm["total_calorie"]} | 蛋白 {sm["total_protein"]}g')
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
