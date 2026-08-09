#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_exercise_strength.py — 力量训练总览 HTML(结果型 · E4.2)

对应 SKILL.md 唤醒词:看力量训练总览
对应模板: templates/exercise_strength.html

呈现数据(权威清单 §4):按动作聚合的表(总组数/总重量/次数)+ 重量轨迹小图。
口径(2026-08-02):总重量 = Σ(load_kg × reps),load_kg 为单侧重量(回执标注口径)。
"""
import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'exercise_strength.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_scene_path  # noqa
from render_crud_view import _chain_valid, _quote_arg  # noqa


def build_data(days: int = 90):
    from db import find_db_path
    import sqlite3
    from datetime import date, timedelta
    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    start = (date.today() - timedelta(days=days - 1)).isoformat()
    rows = conn.execute(
        "SELECT date, exercise_type, set_index, load_kg, reps FROM exercise_log "
        "WHERE category = '力量' AND date >= ? AND COALESCE(is_deleted, 0) = 0 "
        "ORDER BY date ASC, exercise_type ASC, set_index ASC",
        (start,)).fetchall()
    conn.close()

    by_action: dict[str, dict] = {}
    series: dict[str, list] = {}
    for d, etype, set_idx, load, reps in rows:
        load = load or 0
        reps = reps or 0
        a = by_action.setdefault(etype, {'sets': 0, 'weight': 0.0, 'reps': 0, 'count': 0})
        a['sets'] += 1
        a['weight'] += load * reps
        a['reps'] += reps
        a['count'] += 1
        series.setdefault(etype, []).append({'date': d, 'weight': round(load * reps, 1)})

    actions = sorted(by_action.items(), key=lambda kv: -kv[1]['sets'])
    total_sets = sum(a['sets'] for _, a in actions)
    total_weight = round(sum(a['weight'] for _, a in actions), 1)
    total_reps = sum(a['reps'] for _, a in actions)

    # 轨迹:每动作最近 10 个训练日
    trends = []
    for etype, pts in series.items():
        by_date = {}
        for pt in pts:
            by_date[pt['date']] = by_date.get(pt['date'], 0) + pt['weight']
        dates = sorted(by_date)[-10:]
        trends.append({'action': etype, 'points': [{'date': d, 'weight': by_date[d]} for d in dates]})

    return {
        'status': 'ok',
        'data': {
            'summary': {
                'subtitle': f'最近 {days} 天 · {len(actions)} 个动作 · {total_sets} 组',
                'k1': {'label': '动作数', 'value': str(len(actions)), 'extra': f'{days} 天内'},
                'k2': {'label': '总组数', 'value': f'{total_sets}', 'extra': f'共 {total_reps} 次'},
                'k3': {'label': '总重量', 'value': f'{total_weight:,.1f} kg', 'extra': '单侧口径 Σ(kg×次数)'},
                'k4': {'label': '平均每组', 'value': f'{round(total_reps / max(1, total_sets), 1)} 次',
                       'extra': f'{round(total_weight / max(1, total_sets), 1)} kg/组'},
                'table_header': ("<tr><th>动作</th><th class='num'>总组数</th>"
                                 "<th class='num'>总重量</th><th class='num'>总次数</th></tr>"),
                'table_title': '按动作聚合',
            },
            'actions': [{'name': name, 'sets': a['sets'], 'weight': round(a['weight'], 1),
                         'reps': a['reps']} for name, a in actions],
            'trends': trends,
            'meta': {'days': days, 'today': date.today().isoformat()},
        },
        'message': f'已生成力量训练总览({len(actions)} 个动作)',
    }


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


def main():
    p = argparse.ArgumentParser(description='渲染力量训练总览 HTML')
    p.add_argument('--days', type=int, default=90)
    p.add_argument('--chain', help='AI 思考链(必填·强制规则 · 2026-08-02)')
    p.add_argument('--output')
    args = p.parse_args()
    if not _chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        print('   未传 = AI 未按 SKILL.md 流程执行,行为不可控。', file=sys.stderr)
        return 2
    try:
        data = build_data(args.days)
        data['data']['meta'] = {'chain': args.chain.strip(), 'wake_word': '看力量训练总览'}
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, '看力量训练总览', 'result')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    print(f'✅ {out_path}')
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
