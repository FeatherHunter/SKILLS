#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_weight_dashboard.py — 看体重总览 / 看今日体重 结果 HTML 渲染器(ticket #4)

对应 SKILL.md 唤醒词:
  - 看体重总览  → --view overview(5 KPI:当前/Δ7天/距历史最低/距目标/波动等级 + 7 天趋势小图 + 一句话)
  - 看今日体重  → --view today(今日体重/距上次/一句话)
对应模板: templates/weight_dashboard.html
用法:
  python scripts/render_weight_dashboard.py --view overview --chain "1.识别→2.读DB→3.渲染"
  python scripts/render_weight_dashboard.py --view today --chain "1.识别→2.读DB→3.渲染"
"""
import argparse, json, statistics, sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'weight_dashboard.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_scene_path  # noqa
from render_crud_view import _chain_valid, _quote_arg  # noqa


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


def _db():
    from db import find_db_path, get_db
    return get_db(find_db_path(SKILL_DIR))


def _rows(start, end):
    conn = _db()
    cur = conn.cursor()
    cur.execute('SELECT date, weight_kg FROM weight_log WHERE date BETWEEN ? AND ? ORDER BY date', (start, end))
    rows = cur.fetchall()
    conn.close()
    return rows


def build_overview():
    today = date.today()
    rows = _rows('2000-01-01', today.isoformat())
    if not rows:
        return None, '无体重记录'
    current = rows[-1][1]
    # 近 7 天
    week_start = today - timedelta(days=6)
    week = _rows(week_start.isoformat(), today.isoformat())
    delta_7d = round(week[-1][1] - week[0][1], 1) if len(week) >= 2 else None
    # 距历史最低
    min_kg = min(r[1] for r in rows)
    min_date = next(r[0] for r in rows if r[1] == min_kg)
    diff_min = round(current - min_kg, 1)
    # 距目标
    conn = _db()
    cur = conn.cursor()
    cur.execute('SELECT weight_goal FROM daily_goal WHERE id = 1')
    g = cur.fetchone()
    conn.close()
    goal = g[0] if g and g[0] else None
    diff_target = round(current - goal, 1) if goal else None
    # 波动等级(近 30 天标准差)
    month = _rows((today - timedelta(days=29)).isoformat(), today.isoformat())
    std = round(statistics.stdev([r[1] for r in month]), 2) if len(month) > 1 else 0
    vol_level = '稳定' if std < 0.3 else ('正常' if std < 0.5 else '波动较大')
    vol_cls = 'good' if std < 0.3 else ('warn' if std < 0.5 else 'bad')
    # 7 天趋势点
    trend_points = [{'date': r[0], 'kg': r[1]} for r in week]
    # 2026-08-10 #43 审查:0 值显示 "0.0" 不带正负号(+0.0 视觉误导)
    def _d(v):
        return '0.0' if (v is not None and abs(v) < 0.05) else f'{v:+.1f}'
    summary = f"当前 {current}kg · 近 7 天 {_d(delta_7d)}kg" if delta_7d is not None else f"当前 {current}kg"
    if diff_min is not None:
        summary += f" · 距历史最低 {_d(diff_min)}kg"
    if diff_target is not None:
        summary += f" · 距目标 {_d(diff_target)}kg"
    summary += f" · 波动{vol_level}"
    kpis = [
        {'label': '当前体重', 'value': f'{current} kg', 'extra': f'{rows[-1][0]}'},
        {'label': '近 7 天变化',
         'value': ('—' if delta_7d is None else ('0.0 kg' if abs(delta_7d) < 0.05 else f'{delta_7d:+.1f} kg')),
         'extra': 'Δ7 天',
         'cls': '' if (delta_7d is None or abs(delta_7d) < 0.05) else ('good' if delta_7d < 0 else 'bad')},
        {'label': '距历史最低', 'value': (_d(diff_min) + ' kg'), 'extra': f'最低 {min_kg} kg ({min_date[-5:]})'},
        {'label': '距目标', 'value': ((_d(diff_target) + ' kg') if diff_target is not None else '—'),
         'extra': f'目标 {goal}kg' if goal else '未设目标'},
        {'label': '波动等级', 'value': vol_level, 'extra': f'σ {std}', 'cls': vol_cls},
    ]
    return {
        'view': 'overview',
        'title': '看体重总览',
        'subtitle': f'{rows[0][0]} ~ {today.isoformat()} · 共 {len(rows)} 条',
        'kpis': kpis,
        'trend_points': trend_points,
        'trend_title': '最近 7 天趋势',
        'summary': summary,
    }, None


def build_today():
    today = date.today()
    rows = _rows('2000-01-01', today.isoformat())
    if not rows:
        return None, '今天无体重记录'
    if rows[-1][0] != today.isoformat():
        return None, f'今天还没记录体重(最近记录 {rows[-1][0]} {rows[-1][1]}kg)'
    current = rows[-1][1]
    prev = rows[-2][1] if len(rows) >= 2 else None
    delta_last = round(current - prev, 1) if prev else None
    # 一句话
    if delta_last is None:
        one_line = f'今日体重 {current}kg(首条记录)'
    else:
        one_line = f'今日 {current}kg,较上次{"+" if delta_last > 0 else ""}{delta_last}kg'
    return {
        'view': 'today',
        'title': '看今日体重',
        'subtitle': f'{today.isoformat()} · 今日记录',
        'kpis': [
            {'label': '今日体重', 'value': f'{current} kg', 'extra': today.isoformat()},
            {'label': '较上次',
             'value': ('—' if delta_last is None else ('0.0 kg' if abs(delta_last) < 0.05 else f'{delta_last:+.1f} kg')),
             'cls': '' if (delta_last is None or abs(delta_last) < 0.05) else ('bad' if delta_last > 0 else 'good')},
        ],
        'today_kg': current,
        'today_date': today.isoformat(),
        'delta_last': delta_last,
        'summary': one_line,
    }, None


def main():
    p = argparse.ArgumentParser(description='渲染体重总览/今日体重 HTML(ticket #4)')
    p.add_argument('--view', choices=['overview', 'today'], default='overview')
    p.add_argument('--chain', help='AI 思考链(必填·强制规则 · 2026-08-02)')
    p.add_argument('--output')
    args = p.parse_args()

    if not _chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        return 2

    try:
        data, err = build_overview() if args.view == 'overview' else build_today()
        if err:
            print(f'❌ {err}', file=sys.stderr)
            return 1
        data['meta'] = {'generated_at': date.today().isoformat(), 'chain': args.chain.strip(),
                        'wake_word': '看体重总览' if args.view == 'overview' else '看今日体重'}
        argv = sys.argv[1:]
        if '--output' in argv:
            i = argv.index('--output')
            argv = argv[:i] + argv[i + 2:] if i + 1 < len(argv) else argv[:i]
        data['meta']['render_cmd'] = f"python scripts/{Path(__file__).name} " + ' '.join(_quote_arg(a) for a in argv)
        data['meta']['source'] = 'weight_log (今日)' if args.view == 'today' else 'weight_log (总览)'
        payload = {'status': 'ok', 'data': data, 'message': '已生成体重总览'}
        html = render_html(payload)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    scene_name = '看体重总览' if args.view == 'overview' else '看今日体重'
    out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, scene_name, 'result')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    print(f'✅ {out_path}')
    print(f'   视图: {args.view}')
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
