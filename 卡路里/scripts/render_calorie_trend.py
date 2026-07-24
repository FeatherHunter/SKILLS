#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_calorie_trend.py — 热量趋势 HTML 渲染器(报告型 · 7 dim)

对应 SKILL.md 唤醒词: 查热量趋势
对应模板: templates/calorie_trend.html
- 输出目录: $DATA_DIR/calorie_html/calorie_trend_<TS>.html (手册 §4.1)
- 占位符: <!--INJECT-DATA--> 恰好 1 次
"""
import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'calorie_trend.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa: E402


def _load_data(input_path):
    """从 mock JSON 加载 (status|ok|error 契约)"""
    raw = json.loads(Path(input_path).read_text(encoding='utf-8'))
    if raw.get('status') != 'ok':
        raise ValueError(f"数据状态非 ok: {raw.get('message')}")
    return raw


def _build_data_from_db(start, end):
    """从 DB 真实查询 — 调 analysis.diet.diet_calorie_trend"""
    from diet_calorie_trend import diet_calorie_trend  # type: ignore
    raw = diet_calorie_trend(start=start, end=end)
    return {
        'status': 'ok',
        'data': raw,
        'message': f'已生成 {start} ~ {end} 热量趋势',
    }


def build_data(start, end):
    """聚合 7 dim 数据: 日均/趋势/工作日vs周末/合规率 + 每日 series"""
    from db import find_db_path
    import sqlite3

    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # 取每日的 calorie 总和 + 目标(取 daily_goal.calorie)
    cur.execute("""
        SELECT date, COALESCE(SUM(calorie), 0)
        FROM food_log
        WHERE date BETWEEN ? AND ?
        GROUP BY date
        ORDER BY date
    """, (start, end))
    daily = dict(cur.fetchall())

    cur.execute("SELECT calorie FROM daily_goal ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    target = row[0] if row else 1800
    conn.close()

    # 生成每日 series (含周末判定)
    series = []
    s = datetime.fromisoformat(start)
    e = datetime.fromisoformat(end)
    today = date.today().isoformat()
    cur_d = s
    while cur_d <= e:
        ds = cur_d.strftime('%Y-%m-%d')
        cal = daily.get(ds, 0)
        weekday = '周' + '一二三四五六日'[cur_d.weekday()]
        if cur_d.weekday() >= 5:
            weekday_type = '周末'
        else:
            weekday_type = '工作日'
        series.append({
            'date': ds,
            'weekday': weekday,
            'type': weekday_type,
            'calorie': cal,
        })
        cur_d += timedelta(days=1)

    # 聚合
    n = len(series)
    total = sum(s['calorie'] for s in series)
    avg = round(total / n) if n else 0
    weekday_avg = round(sum(s['calorie'] for s in series if s['type'] == '工作日') /
                       max(1, sum(1 for s in series if s['type'] == '工作日')))
    weekend_avg = round(sum(s['calorie'] for s in series if s['type'] == '周末') /
                       max(1, sum(1 for s in series if s['type'] == '周末')))
    weekend_diff = weekend_avg - weekday_avg
    compliant_days = sum(1 for s in series if s['calorie'] <= target * 1.05)
    compliance_rate = round(compliant_days / n, 2) if n else 0

    # 趋势方向: 用首尾两天对比
    if n >= 2:
        start_avg = series[0]['calorie']
        end_avg = series[-1]['calorie']
        trend_value = end_avg - start_avg
        trend = 'down' if trend_value < -50 else 'up' if trend_value > 50 else 'flat'
    else:
        start_avg = end_avg = avg
        trend_value = 0
        trend = 'flat'

    return {
        'status': 'ok',
        'data': {
            'summary': {
                'avg': avg,
                'target': target,
                'trend': trend,
                'trend_value': trend_value,
                'start_avg': start_avg,
                'end_avg': end_avg,
                'weekday_avg': weekday_avg,
                'weekend_avg': weekend_avg,
                'weekend_diff': weekend_diff,
                'compliance_rate': compliance_rate,
                'compliant_days': compliant_days,
            },
            'series': series,
            'meta': {
                'start': start,
                'end': end,
                'today': today,
                'weekday_count': sum(1 for s in series if s['type'] == '工作日'),
                'weekend_count': sum(1 for s in series if s['type'] == '周末'),
            },
        },
        'message': f'已生成 {start} ~ {end} 热量趋势({n} 天)',
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
    p = argparse.ArgumentParser(description='渲染热量趋势 HTML(报告型 · 7 dim)')
    p.add_argument('--start', help='开始日期 YYYY-MM-DD(默认 7 天前)')
    p.add_argument('--end', help='结束日期 YYYY-MM-DD(默认今天)')
    p.add_argument('--days', type=int, help='近 N 天(覆盖 --start/--end)')
    p.add_argument('--mock', help='从 mock JSON 文件加载数据(代替 DB 查询)')
    p.add_argument('--output', help='输出文件路径(默认 calorie_html/calorie_trend_<TS>.html)')
    args = p.parse_args()

    if args.days:
        end_dt = date.today()
        start_dt = end_dt - timedelta(days=args.days - 1)
        start, end = start_dt.isoformat(), end_dt.isoformat()
    else:
        end = args.end or date.today().isoformat()
        start = args.start or (date.today() - timedelta(days=6)).isoformat()

    try:
        if args.mock:
            data = _load_data(args.mock)
        else:
            data = build_data(start, end)
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    if args.output:
        out_path = Path(args.output)
    else:
        out_path = html_path(SKILL_DIR, 'calorie_trend')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')

    s = data['data']['summary']
    print(f'✅ {out_path}')
    print(f'   范围: {start} ~ {end} | 日均: {s["avg"]:,} 卡 | 趋势: {s["trend"]} ({s["trend_value"]:+d}) | 合规: {int(s["compliance_rate"]*100)}%')
    return 0


if __name__ == '__main__':
    sys.exit(main())
