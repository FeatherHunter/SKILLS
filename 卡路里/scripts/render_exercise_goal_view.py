#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_exercise_goal_view.py — 运动目标达成视图 HTML(结果型 · E3.10/11)

对应 SKILL.md 唤醒词(2 个):
  - 看今日运动（vs 目标） → --period today
  - 看本周运动（vs 目标） → --period week(周目标 = 日目标×7)
对应模板: templates/exercise_goal_view.html

呈现数据(权威清单 §4 E3.10/11):大进度环/进度条(完成度)+ 距目标差额 + 达标/未达标判断 + 一句话。

交互规则(2026-08-02 · SKILL.md):daily_goal.exercise_goal 未设时,AI 先问用户
「每天运动消耗目标(卡)」并写库(INSERT OR REPLACE),之后每次直接展示。
未设目标时本渲染器输出空状态,由 AI 引导首问。
"""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'exercise_goal_view.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_scene_path  # noqa
from render_crud_view import _chain_valid, _quote_arg  # noqa
from exercise_tracker import resolve_window  # noqa


def _read_goal() -> int | None:
    """读每日运动目标(卡);未设返回 None"""
    from db import find_db_path
    import sqlite3
    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT exercise_goal FROM daily_goal WHERE id = 1").fetchone()
        return row[0] if row and row[0] else None
    finally:
        conn.close()


def _sum_calories(start, end) -> int:
    from db import find_db_path
    import sqlite3
    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT COALESCE(SUM(calories_burned), 0) FROM exercise_log "
            "WHERE date BETWEEN ? AND ? AND COALESCE(is_deleted, 0) = 0",
            (start, end)).fetchone()
        return int(row[0])
    finally:
        conn.close()


def build_data(period: str):
    goal = _read_goal()
    now = date.today()
    if period == 'week':
        start, end = resolve_window('week')
        target = goal * 7 if goal else None
        label = '本周'
    else:
        start, end = now.isoformat(), now.isoformat()
        target = goal
        label = '今日'

    actual = _sum_calories(start, end)

    if goal is None:
        summary = ('未设置每日运动目标 — 请先问用户「每天运动消耗目标(卡)」'
                   '(如 300 卡),写入 daily_goal.exercise_goal 后再展示达成视图')
        return {
            'status': 'ok',
            'data': {
                'period': period, 'goal': None, 'actual': actual, 'pct': None,
                'gap': None, 'achieved': None, 'range': {'start': start, 'end': end},
                'summary': summary,
                'meta': {'today': now.isoformat()},
            },
            'message': '运动目标未设置(空状态)',
        }

    pct = round(actual / target * 100) if target else 0
    gap = target - actual
    achieved = actual >= target
    if achieved:
        verdict = '达标 ✓'
        one_line = f'{label}运动消耗 {actual} 卡,已达成目标 {target} 卡(超额 {abs(gap)} 卡)'
    else:
        verdict = '未达标'
        one_line = f'{label}运动消耗 {actual} 卡,距目标 {target} 卡还差 {gap} 卡(完成 {pct}%)'

    return {
        'status': 'ok',
        'data': {
            'period': period,
            'goal': target, 'actual': actual, 'pct': min(pct, 999),
            'gap': gap, 'achieved': achieved, 'verdict': verdict,
            'range': {'start': start, 'end': end},
            'summary': one_line,
            'meta': {'today': now.isoformat(), 'daily_goal': goal},
        },
        'message': f'已生成{label}运动目标达成视图',
    }


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


def main():
    p = argparse.ArgumentParser(description='渲染运动目标达成视图 HTML')
    p.add_argument('--period', choices=['today', 'week'], default='today')
    p.add_argument('--chain', help='AI 思考链(必填·强制规则 · 2026-08-02)')
    p.add_argument('--output')
    args = p.parse_args()

    if not _chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        print('   未传 = AI 未按 SKILL.md 流程执行,行为不可控。', file=sys.stderr)
        print('   请传入你的实际处理步骤,例如:', file=sys.stderr)
        print('     --chain "1.识别唤醒词→2.读目标与消耗→3.渲染达成视图"', file=sys.stderr)
        return 2

    scene = '看今日运动（vs 目标）' if args.period == 'today' else '看本周运动（vs 目标）'
    try:
        data = build_data(args.period)
        data['data']['meta']['chain'] = args.chain.strip()
        data['data']['meta']['wake_word'] = scene
        argv = sys.argv[1:]
        if '--output' in argv:
            i = argv.index('--output')
            argv = argv[:i] + argv[i + 2:] if i + 1 < len(argv) else argv[:i]
        data['data']['meta']['render_cmd'] = f"python scripts/{Path(__file__).name} " + ' '.join(
            _quote_arg(a) for a in argv)
        data['data']['meta']['source'] = 'daily_goal.exercise_goal + exercise_log (只读达成视图)'
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, scene, 'result')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    d = data['data']
    print(f'✅ {out_path}')
    print(f'   周期: {args.period} | 目标: {d["goal"]} | 实际: {d["actual"]} | '
          f'完成: {d["pct"]}% | {"达标" if d["achieved"] else "未达标"}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
