#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_exercise_summary.py — 运动报表 HTML(共用 4 mode)

对应 SKILL.md 唤醒词:
  - 查运动记录 → mode='records' (默认)
  - 查运动汇总 → mode='summary'
  - 查运动类型 → mode='stats'
  - 查运动趋势 → mode='trend'
对应模板: templates/exercise_summary.html
"""
import argparse, json, sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'exercise_summary.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa


_CAT_LABELS = {'力量':'strength', '有氧':'cardio', '柔韧':'flex', '日常':'daily'}


def _load_data(input_path):
    raw = json.loads(Path(input_path).read_text(encoding='utf-8'))
    if raw.get('status') != 'ok':
        raise ValueError('数据状态非 ok')
    return raw


def _fetch(conn, start, end):
    cur = conn.cursor()
    cur.execute('''
        SELECT date, time, exercise_type, category, calories_burned AS calorie, duration_minutes AS minutes, COALESCE(set_index, 0) AS sets
        FROM exercise_log
        WHERE date BETWEEN ? AND ?
        ORDER BY date DESC, time DESC
    ''', (start, end))
    items = []
    for d, t, et, cat, cal, mins, sets in cur.fetchall():
        cat_key = _CAT_LABELS.get(cat, 'daily')
        items.append({'date': d, 'time': t, 'exercise_type': et,
                      'category': cat_key, 'calorie': cal,
                      'minutes': mins, 'sets': sets or 0})
    return items


def build_data(start, end, mode='records'):
    from db import find_db_path
    import sqlite3
    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    items = _fetch(conn, start, end)
    conn.close()

    days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    if not items:
        return empty_data(start, end, days, mode)

    summary = {
        'records':   build_records_summary(items),
        'summary':   build_summary_summary(items, days),
        'stats':     build_stats_summary(items),
        'trend':     build_trend_summary(items, days),
    }[mode]

    return {
        'status': 'ok',
        'data': {
            'summary': summary,
            'items': items if mode != 'stats' else [],
            'stats': summary.get('_stats_obj'),
            'mode': mode,
            'meta': {'start': start, 'end': end, 'days': days, 'today': date.today().isoformat()},
        },
        'message': f'已生成运动报表({mode}, {len(items)} 条)',
    }


def empty_data(start, end, days, mode):
    return {'status': 'ok', 'data': {'summary': {}, 'items': [], 'mode': mode,
             'meta': {'start': start, 'end': end, 'days': days, 'today': date.today().isoformat()}},
            'message': f'无数据'}


def build_records_summary(items):
    total = round(sum((i.get('calorie') or 0) for i in items), 1)
    total_min = sum((i.get('minutes') or 0) for i in items)
    return {
        'subtitle': f'近 {len(items)} 条运动记录',
        'k1': {'label': '总记录数', 'value': str(len(items)), 'extra': f'共 {len(items)} 条'},
        'k2': {'label': '总热量', 'value': f'{total:,}', 'extra': f'日均 {round(total/30)} 卡'},
        'k3': {'label': '总时长', 'value': f'{total_min} 分钟', 'extra': f'平均 {round(total_min/max(1,len(items)), 1)} 分/次'},
        'k4': {'label': '类型数', 'value': f'{len(set(i["category"] for i in items))} 类', 'extra': '力量/有氧/柔韧/日常'},
        'table_header': "<tr><th>日期</th><th>时间</th><th>类型</th><th class='num'>时长</th><th class='num'>热量</th><th class='num'>组数</th></tr>",
        'table_title': '运动记录'
    }


def build_summary_summary(items, days):
    active_days = len(set(i['date'] for i in items))
    total_cal = round(sum((i.get('calorie') or 0) for i in items), 1)
    total_min = sum((i.get('minutes') or 0) for i in items)
    avg_cal = round(total_cal / max(1, len(items)))
    return {
        'subtitle': f'{days} 天内 {active_days} 天运动',
        'k1': {'label': '运动天数', 'value': str(active_days), 'extra': f'占 {days} 天的 {round(active_days/days*100)}%'},
        'k2': {'label': '总热量', 'value': f'{total_cal:,.1f}', 'extra': f'日均 {round(total_cal/days)}'},
        'k3': {'label': '总时长', 'value': f'{total_min} 分钟', 'extra': f'平均 {round(total_min/max(1,active_days))} 分/天'},
        'k4': {'label': '平均每次', 'value': f'{avg_cal} 卡', 'extra': f'{round(total_min/max(1,len(items)), 1)} 分钟'},
        'table_header': "<tr><th>日期</th><th>时间</th><th>类型</th><th class='num'>时长</th><th class='num'>热量</th><th class='num'>组数</th></tr>",
        'table_title': '运动记录汇总'
    }


def build_stats_summary(items):
    by_cat = {'strength':{'count':0,'calorie':0,'minutes':0,'sets':0},
              'cardio':  {'count':0,'calorie':0,'minutes':0,'sets':0},
              'flex':    {'count':0,'calorie':0,'minutes':0,'sets':0},
              'daily':   {'count':0,'calorie':0,'minutes':0,'sets':0}}
    for i in items:
        c = by_cat[i['category']]
        c['count'] += 1
        c['calorie'] += (i.get('calorie') or 0)
        c['minutes'] += (i.get('minutes') or 0)
        c['sets'] += (i.get('sets') or 0)
    total_cal = sum(c['calorie'] for c in by_cat.values())
    total_cnt = sum(c['count'] for c in by_cat.values())
    total_min = sum(c['minutes'] for c in by_cat.values())
    total_set = sum(c['sets'] for c in by_cat.values())
    return {
        'subtitle': f'按 4 分类(力量/有氧/柔韧/日常)统计',
        'k1': {'label':'总次数', 'value':str(total_cnt), 'extra':'全部运动'},
        'k2': {'label':'总热量', 'value':f'{total_cal:,.1f}', 'extra':'4 类合计'},
        'k3': {'label':'总时长', 'value':f'{total_min} 分钟', 'extra':f'平均 {round(total_min/max(1,total_cnt))} 分/次'},
        'k4': {'label':'总组数', 'value':str(total_set), 'extra':'含力量训练的组数'},
        'table_header': "<tr><th>类型</th><th class='num'>次数</th><th class='num'>热量</th><th>占比</th><th class='num'>时长</th><th class='num'>组数</th></tr>",
        'table_title': '按类型统计',
        '_stats_obj': {
            'by_category': by_cat,
            'total_count': total_cnt,
            'total_calorie': total_cal,
            'total_minutes': total_min,
            'total_sets': total_set
        }
    }


def build_trend_summary(items, days):
    by_date = {}
    for i in items:
        d = i['date']
        if d not in by_date: by_date[d] = 0
        by_date[d] += (i.get('calorie') or 0)
    series = [{'date': d, 'calorie': c} for d, c in sorted(by_date.items())]
    total = sum(s['calorie'] for s in series)
    return {
        'subtitle': f'{len(series)} 个有运动日 · 总 {round(total,1)} 卡 · 日均 {round(total/max(1,days),1)}',
        'k1': {'label':'运动天数', 'value':str(len(series)), 'extra':f'占 {days} 天'},
        'k2': {'label':'总热量', 'value':f'{round(total,1):,}', 'extra':f'日均 {round(total/max(1,len(series)),1)}/运动日'},
        'k3': {'label':'峰值', 'value':f'{round(max(s["calorie"] for s in series), 1) if series else 0:,}', 'extra':'单日最高'},
        'k4': {'label':'趋势', 'value':'↑/↓', 'extra':f'对比 {days//2 if days > 1 else 1} 天前'},
        'table_header': "<tr><th>日期</th><th>时间</th><th>类型</th><th class='num'>时长</th><th class='num'>热量</th><th class='num'>组数</th></tr>",
        'table_title': '每日运动热量',
        '_stats_obj': None
    }


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


def main():
    p = argparse.ArgumentParser(description='渲染运动报表 HTML(共用 4 mode)')
    p.add_argument('--start')
    p.add_argument('--end')
    p.add_argument('--days', type=int, default=7)
    p.add_argument('--mode', choices=['records','summary','stats','trend'], default='records')
    p.add_argument('--mock')
    p.add_argument('--output')
    args = p.parse_args()
    if not args.start or not args.end:
        end_d = date.today()
        start_d = end_d - timedelta(days=args.days - 1)
        s, e = start_d.isoformat(), end_d.isoformat()
    else:
        s, e = args.start, args.end
    try:
        data = _load_data(args.mock) if args.mock else build_data(s, e, mode=args.mode)
        if 'mode' not in data['data']: data['data']['mode'] = args.mode
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, f'exercise_{args.mode}')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    n = len(data['data']['items'])
    print(f'✅ {out_path}')
    print(f'   模式: {args.mode} | 范围: {s} ~ {e} | {n} 条')
    return 0


if __name__ == '__main__':
    sys.exit(main())
