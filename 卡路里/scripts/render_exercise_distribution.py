#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_exercise_distribution.py — 运动分布/贡献 HTML 渲染器(报告型 · 双模式)

对应 SKILL.md 唤醒词:
  - 查运动分布 → mode='distribution' (默认)
  - 查运动贡献 → mode='contribution'
对应模板: templates/exercise_distribution.html
"""
import argparse, json, sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'exercise_distribution.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa


def _load_data(input_path):
    raw = json.loads(Path(input_path).read_text(encoding='utf-8'))
    if raw.get('status') != 'ok':
        raise ValueError(f"数据状态非 ok")
    return raw


def build_data(start, end, mode='distribution', tdee=1700):
    from db import find_db_path
    import sqlite3
    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    # 取每日运动 + 摄入
    cur.execute("""
        SELECT date, type, category, calories, minutes, sets, count(*)
        FROM exercise_log
        WHERE date BETWEEN ? AND ?
        GROUP BY date, type, category ORDER BY date
    """, (start, end))
    rows = cur.fetchall()
    cur.execute("""
        SELECT date, COALESCE(SUM(calorie), 0)
        FROM food_log WHERE date BETWEEN ? AND ?
        GROUP BY date
    """, (start, end))
    intake_by_day = dict(cur.fetchall())
    conn.close()

    # 4 分类
    buckets = {'strength':{'count':0,'calorie':0,'minutes':0},
               'cardio':   {'count':0,'calorie':0,'minutes':0},
               'flex':     {'count':0,'calorie':0,'minutes':0},
               'daily':    {'count':0,'calorie':0,'minutes':0}}
    _CAT_MAP = {'力量':'strength','有氧':'cardio','柔韧':'flex','日常':'daily'}
    for date_, type_, cat, cal, mins, sets, n in rows:
        key = _CAT_MAP.get(cat, 'daily')
        buckets[key]['count'] += n
        buckets[key]['calorie'] += cal
        buckets[key]['minutes'] += mins

    days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    active_days = len({r[0] for r in rows})
    total_calorie = sum(b['calorie'] for b in buckets.values())
    total_min = sum(b['minutes'] for b in buckets.values())
    total_sets = sum(b['count'] for b in buckets.values())
    avg_cal = round(total_calorie / days) if days else 0
    avg_min = round(total_min / max(active_days, 1))
    avg_set = round(total_sets / max(active_days, 1))

    total_intake = sum(intake_by_day.values())
    weekly_deficit = tdee * days + total_calorie - total_intake
    contrib_pct = round(total_calorie / max(total_intake, 1) * 100, 1)

    base = {
        'summary': {
            'active_days': active_days,
            'total_calorie': total_calorie,
            'avg_calorie': avg_cal,
            'total_minutes': total_min,
            'avg_minutes': avg_min,
            'total_sets': total_sets,
            'avg_sets': avg_set,
            'contribution_pct': contrib_pct,
            'weekly_deficit': weekly_deficit,
        },
        'breakdown': buckets,
        'contrib': {
            'exercise': total_calorie,
            'tdee': tdee * days,
            'intake': total_intake,
            'exercise_pct': contrib_pct,
            'intake_pct': 100,
            'weekly_deficit': weekly_deficit,
            'contribution_pct': contrib_pct,
        },
        'series': [{'date': start, 'total_calorie': total_calorie}] * days,
        'meta': {'start': start, 'end': end, 'days': days, 'today': date.today().isoformat()},
        'mode': mode,
    }
    return {'status': 'ok', 'data': base, 'message': f'已生成 {start} ~ {end} 运动{mode}({days} 天)'}


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


def main():
    p = argparse.ArgumentParser(description='渲染运动分布/贡献 HTML(报告型)')
    p.add_argument('--start')
    p.add_argument('--end')
    p.add_argument('--days', type=int)
    p.add_argument('--mode', choices=['distribution','contribution'], default='distribution')
    p.add_argument('--mock', help='mock JSON 文件(代替 DB 查询)')
    p.add_argument('--tdee', type=int, default=1700)
    p.add_argument('--output')
    args = p.parse_args()
    if args.days:
        end_d = date.today()
        start_d = end_d - timedelta(days=args.days - 1)
    else:
        end_d = date.fromisoformat(args.end or date.today().isoformat())
        start_d = date.fromisoformat(args.start or (end_d - timedelta(days=6)).isoformat())
    s, e = start_d.isoformat(), end_d.isoformat()
    try:
        data = _load_data(args.mock) if args.mock else build_data(s, e, mode=args.mode, tdee=args.tdee)
        # mock 缺 mode 字段时手动注入
        if 'mode' not in data.get('data', {}):
            data['data']['mode'] = args.mode
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, f'exercise_{args.mode}')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    sm = data['data']['summary']
    print(f'✅ {out_path}')
    print(f'   模式: {args.mode} | 范围: {s} ~ {e} | 运动 {sm["active_days"]}/{data["data"]["meta"]["days"]} 天 | {sm["total_calorie"]} 卡')
    return 0


if __name__ == '__main__':
    sys.exit(main())
