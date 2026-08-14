#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_calorie_deficit.py — 热量缺口分析 HTML 渲染器(报告型 · 摄入 vs 消耗)

对应 SKILL.md 唤醒词: 查热量缺口
对应模板: templates/calorie_deficit.html

v2 · 2026-08-13 T5 薄壳化(map #349):
  - 数据源委托 analysis/series.py::build_series(ADR-0013 单一真相源, TDEE 口径)
  - 热量缺口 = 消耗 − 摄入, 正=缺口(修复原 3 处错误列名 + tdee−300 假设 + 符号反向)
  - 不再自算缺口, 无独立口径可漂移
"""

from _base_render import render_template, write_html  # noqa: E402
COMMAND_CN = '查热量缺口'
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


def build_data(start, end):
    """热量缺口分析: 摄入 vs 运动消耗 vs TDEE (数据源 = analysis.series)

    热量缺口 = 消耗 − 摄入, 正=缺口=减重潜力(ADR-0013)。
    消耗 = TDEE(档案 BMR×活动系数) + 当日运动消耗; 摄入 = 当日食物热量(不含饮水)。
    """
    from analysis.series import build_series
    s = build_series(start, end)

    target_intake = (s[0].get('calorie_goal') if s else None) or 1800
    tdee = s[0].get('tdee') if s else 1800

    # 生成每日 series(模板消费字段: date/intake/burn/deficit/weekday)
    series = []
    total_i = total_b = total_d = 0
    for day in s:
        ds = day['date']
        intake = day.get('calories') or 0
        exercise_burn = day.get('exercise_kcal') or 0
        burn = (day.get('tdee') or 0) + exercise_burn  # 消耗 = TDEE + 运动
        deficit = day.get('deficit') or 0              # series 已按 正=缺口 计算
        series.append({
            'date': ds,
            'intake': intake,
            'burn': burn,
            'deficit': deficit,
            'weekday': '周' + '一二三四五六日'[date.fromisoformat(ds).weekday()],
        })
        total_i += intake; total_b += burn; total_d += deficit

    n = len(series)
    avg_i = round(total_i / n) if n else 0
    avg_b = round(total_b / n) if n else 0
    avg_ex = round(sum((x.get('exercise_kcal') or 0) for x in s) / n) if n else 0
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
                'today': date.today().isoformat(),
                'weekday_count': weekday_count,
                'weekend_count': weekend_count,
            },
        },
        'message': f'已生成 {start} ~ {end} 热量缺口({days} 天)',
    }


def render_html(data):
    return render_template(TEMPLATE_PATH, data, COMMAND_CN)


def main():
    p = argparse.ArgumentParser(description='渲染热量缺口 HTML(报告型)')
    p.add_argument('--start')
    p.add_argument('--end')
    p.add_argument('--days', type=int)
    p.add_argument('--mock')
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
        data = _load_data(args.mock) if args.mock else build_data(s, e)
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, '热量缺口')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_html(html, out_path)
    sm = data['data']['summary']
    print(f'✅ {out_path}')
    print(f'   范围: {s} ~ {e} | 摄入 {sm["avg_intake"]} / 消耗 {sm["avg_burn"]} | 缺口 {sm["avg_deficit"]:+d} | 7d累计 {sm["weekly_deficit"]:+d} 卡 | 减重 {sm["predicted_loss_kg"]:+.2f}kg')
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
