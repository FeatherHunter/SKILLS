#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_today_water.py — 今日饮水 HTML 渲染器(报告型 · 进度环 + 7 天 mini-chart)

对应 SKILL.md 唤醒词: 查今天喝水(ADR-0003 · 2026-07-29 加)
对应模板: templates/today_water.html
- 输出目录: $DATA_DIR/calorie_html/今日饮水_<TS>.html (手册 §4.1 · v2.4.8 中文化)
- 占位符: <!--INJECT-DATA--> 恰好 1 次
- 数据源: food_log 中 food_name='💧水' 的 grams 聚合(ml) + daily_goal.water_goal
- 7 天范围: 含今天,最早 6 天前
"""
import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'today_water.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa: E402


def _load_data(input_path):
    """从 mock JSON 加载 (status|ok 契约)"""
    raw = json.loads(Path(input_path).read_text(encoding='utf-8'))
    if raw.get('status') != 'ok':
        raise ValueError(f"数据状态非 ok: {raw.get('message')}")
    return raw


def build_data(day):
    """从 calorie_data.db 查今日饮水 + 7 天序列 + 目标"""
    from db import find_db_path
    import sqlite3

    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # 饮水目标:water_goal 列(2026-07-12 加)
    cur.execute("SELECT water_goal FROM daily_goal ORDER BY id DESC LIMIT 1")
    goal_row = cur.fetchone()
    target_ml = int(goal_row[0]) if goal_row and goal_row[0] else 2000

    # 今日饮水:food_log 中 food_name='💧水' 的 grams 聚合
    cur.execute("""
        SELECT COALESCE(SUM(grams), 0)
        FROM food_log
        WHERE date = ? AND food_name = '💧水'
    """, (day,))
    today_ml = int(cur.fetchone()[0] or 0)

    # 今日每杯明细(看今日喝水 呈现数据 · ticket #3)
    cur.execute("""
        SELECT time, grams FROM food_log
        WHERE date = ? AND food_name = '💧水'
        ORDER BY time
    """, (day,))
    cups = [{'time': (t or '')[:5], 'ml': int(g or 0)} for t, g in cur.fetchall()]

    # 7 天(含今天,最早 6 天前)
    week_ml: list[int] = []
    week_dates: list[str] = []
    for i in range(6, -1, -1):
        d = (datetime.fromisoformat(day) - timedelta(days=i)).strftime('%Y-%m-%d')
        cur.execute("""
            SELECT COALESCE(SUM(grams), 0)
            FROM food_log
            WHERE date = ? AND food_name = '💧水'
        """, (d,))
        week_ml.append(int(cur.fetchone()[0] or 0))
        week_dates.append(d)

    conn.close()

    return {
        'status': 'ok',
        'data': {
            'summary': {
                'today_ml':   today_ml,
                'target_ml':  target_ml,
                'week_ml':    week_ml,
                'week_dates': week_dates,
                'cups':       cups,
            },
            'meta': {
                'date':  day,
                'today': date.today().isoformat(),
            },
        },
        'message': f'已生成 {day} 今日饮水({today_ml} ml)',
    }


def render_html(data):
    """注入数据到模板"""
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符 或 重复出现')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    inject = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace('<!--INJECT-DATA-->', inject, 1)


def main():
    p = argparse.ArgumentParser(description='渲染今日饮水 HTML(报告型 · ring + 7天 bar)')
    p.add_argument('--date', help='日期 YYYY-MM-DD(默认今天)')
    p.add_argument('--mock', help='从 mock JSON 文件加载(代替 DB 查询)')
    p.add_argument('--output', help='输出文件路径(默认 calorie_html/今日饮水_<TS>.html)')
    args = p.parse_args()

    day = args.date or date.today().isoformat()
    try:
        if args.mock:
            data = _load_data(args.mock)
        else:
            data = build_data(day)
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    if args.output:
        out_path = Path(args.output)
    else:
        out_path = html_path(SKILL_DIR, '今日饮水')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')

    s = data['data']['summary']
    pct = round(s['today_ml'] / s['target_ml'] * 100) if s['target_ml'] else 0
    print(f'✅ {out_path}')
    print(f'   日期: {day} | 饮水: {s["today_ml"]} / {s["target_ml"]} ml ({pct}%) | 本周 7 天')
    return 0


if __name__ == '__main__':
    sys.exit(main())