#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_diet_overview.py — 看饮食总览 HTML 渲染器(结果型)

对应 SKILL.md 唤醒词: 看饮食总览
对应模板: templates/diet_overview.html

呈现数据(2026-08-01 对抗审查修复):
  本周/本月累计 + 趋势小图;不含今日(今日由主页「看今日饮食概览」承接)
"""
import argparse, json, sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'diet_overview.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa


def _week_range():
    today = date.today()
    start = today - timedelta(days=today.weekday())
    end = today - timedelta(days=1)  # 不含今日
    return start.isoformat(), end.isoformat()


def _month_range():
    today = date.today()
    start = today.replace(day=1)
    end = today - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def _aggregate(start, end):
    from db import find_db_path
    import sqlite3
    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute('''
        SELECT date, SUM(calories), SUM(protein), SUM(carbs), SUM(fat), COUNT(*)
        FROM food_log WHERE date BETWEEN ? AND ? AND food_name != '💧水'
        GROUP BY date ORDER BY date
    ''', (start, end))
    rows = cur.fetchall()
    conn.close()
    days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    total_cal = round(sum(r[1] or 0 for r in rows), 1)
    total_pro = round(sum(r[2] or 0 for r in rows), 1)
    total_carb = round(sum(r[3] or 0 for r in rows), 1)
    total_fat = round(sum(r[4] or 0 for r in rows), 1)
    return {
        'total_cal': total_cal, 'total_pro': total_pro,
        'total_carb': total_carb, 'total_fat': total_fat,
        'days': days, 'with_data_days': len(rows),
        'avg_cal': round(total_cal / max(1, days), 1),
        # #44 审查(D5.3 趋势小图):补全完整窗口——无记录天 0 值占位,趋势连续可见
        'daily': _fill_daily(start, end, rows),
    }


def _fill_daily(start, end, rows):
    by = {r[0]: r[1] or 0 for r in rows}
    from datetime import timedelta as _td
    out = []
    d = date.fromisoformat(start)
    end_d = date.fromisoformat(end)
    while d <= end_d:
        iso = d.isoformat()
        out.append({'date': iso, 'cal': by.get(iso, 0)})
        d += _td(days=1)
    return out


def build_data():
    ws, we = _week_range()
    ms, me = _month_range()
    week = _aggregate(ws, we)
    month = _aggregate(ms, me)
    return {
        'status': 'ok',
        'data': {
            'week': {'start': ws, 'end': we, **week},
            'month': {'start': ms, 'end': me, **month},
            'meta': {'today': date.today().isoformat()},
        },
        'message': f'饮食总览 本周({ws}~{we}) / 本月({ms}~{me}),不含今日',
    }


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


def main():
    p = argparse.ArgumentParser(description='渲染饮食总览 HTML(结果型 · 周期累计)')
    p.add_argument('--output')
    p.add_argument('--chain', help='AI 思考链注入(meta.chain,不进 UI;复制日志可带出 · R3)')
    args = p.parse_args()
    try:
        data = build_data()
        if args.chain:
            data['data']['meta']['chain'] = args.chain
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, '饮食总览')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    print(f'✅ {out_path}')
    print(f'   本周 {data["data"]["week"]["total_cal"]} 卡 / 本月 {data["data"]["month"]["total_cal"]} 卡')
    return 0


if __name__ == '__main__':
    sys.exit(main())
