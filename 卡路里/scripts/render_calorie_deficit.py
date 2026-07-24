#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_calorie_deficit.py — 热量缺口分析 HTML 渲染器(报告型 · 摄入 vs 消耗)

对应 SKILL.md 唤醒词: 查热量缺口
对应模板: templates/calorie_deficit.html
"""
import argparse, json, sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'calorie_deficit.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa: E402

# 7700 kcal/kg 脂肪
KCAL_PER_KG = 7700


def _load_data(input_path):
    raw = json.loads(Path(input_path).read_text(encoding='utf-8'))
    if raw.get('status') != 'ok':
        raise ValueError(f"数据状态非 ok: {raw.get('message')}")
    return raw


def build_data(start, end, tdee=1700):
    """TDEE 静态摄入 + 估算运动燃烧(简化版)

    注:真实场景应调用 analysis/diet.py::diet_deficit_analysis(start, end)
    """
    from db import find_db_path
    import sqlite3
    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    cur.execute("SELECT calorie FROM daily_goal ORDER BY id DESC LIMIT 1")
    g = cur.fetchone() or (1800,)
    target_intake = g[0]

    cur.execute("""
        SELECT date, COALESCE(SUM(calorie), 0) AS intake
        FROM food_log WHERE date BETWEEN ? AND ?
        GROUP BY date ORDER BY date
    """, (start, end))
    intake_by_day = dict(cur.fetchall())

    cur.execute("""
        SELECT date, COALESCE(SUM(calorie), 0) AS burn
        FROM exercise_log WHERE date BETWEEN ? AND ?
        GROUP BY date ORDER BY date
    """, (start, end))
    burn_by_day = dict(cur.fetchall())
    conn.close()

    # 生成每日 series
    series = []
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    today = date.today().isoformat()
    cur_d = s
    total_i = total_b = total_d = 0
    while cur_d <= e:
        ds = cur_d.isoformat()
        intake = intake_by_day.get(ds, 0)
        exercise_burn = burn_by_day.get(ds, 0)
        burn = tdee - 300 + exercise_burn  # 假设 300 是 TEF(食物热效应)
        # 缺口:摄入 - 消耗 (正值=消耗>摄入=减重,负值=过量)
        deficit = burn - intake
        # 摄入目标
        series.append({
            'date': ds,
            'intake': intake,
            'burn': burn,
            'deficit': deficit,
            'weekday': '周' + '一二三四五六日'[cur_d.weekday()],
        })
        total_i += intake; total_b += burn; total_d += deficit
        cur_d += timedelta(days=1)

    n = len(series)
    avg_i = round(total_i / n) if n else 0
    avg_b = round(total_b / n) if n else 0
    avg_ex = round(sum(burn_by_day.values()) / n) if n else 0
    avg_d = round(total_d / n) if n else 0
    weekly_d = total_d
    # 预测减重:每周缺口 / 7700 = kg
    pred_loss = round(weekly_d / KCAL_PER_KG, 2)
    trend = 'loss' if avg_d > 0 else ('gain' if avg_d < 0 else 'flat')
    days = n
    weekday_count = sum(1 for p in series if p['weekday'] in ['周一','周二','周三','周四','周五'])
    weekend_count = days - weekday_count

    return {
        'status': 'ok',
        'data': {
            'summary': {
                'avg_intake': avg_i,
                'avg_burn': avg_b,
                'avg_exercise_burn': avg_ex,
                'avg_deficit': avg_d,
                'weekly_deficit': weekly_d,
                'predicted_loss_kg': pred_loss,
                'trend': trend,
            },
            'target': {
                'intake': target_intake,
                'tdee': tdee,
                'weekly_deficit_per_day': 300,
            },
            'series': series,
            'meta': {
                'start': start, 'end': end, 'days': days,
                'today': today,
                'weekday_count': weekday_count,
                'weekend_count': weekend_count,
            },
        },
        'message': f'已生成 {start} ~ {end} 热量缺口({days} 天)',
    }


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


def main():
    p = argparse.ArgumentParser(description='渲染热量缺口 HTML(报告型)')
    p.add_argument('--start')
    p.add_argument('--end')
    p.add_argument('--days', type=int)
    p.add_argument('--mock')
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
        data = _load_data(args.mock) if args.mock else build_data(s, e, tdee=args.tdee)
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, 'calorie_deficit')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    sm = data['data']['summary']
    print(f'✅ {out_path}')
    print(f'   范围: {s} ~ {e} | 摄入 {sm["avg_intake"]} / 消耗 {sm["avg_burn"]} | 缺口 {sm["avg_deficit"]:+d} | 7d累计 {sm["weekly_deficit"]:+d} 卡 | 减重 {sm["predicted_loss_kg"]:+.2f}kg')
    return 0


if __name__ == '__main__':
    sys.exit(main())
