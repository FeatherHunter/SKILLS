#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_goal_weight.py — 体重目标 HTML 渲染器(体重型)

对应 SKILL.md 唤醒词: 定体重目标 / 定体重目标(自动算截止) / 定体重目标(含起始日) / 改体重目标
对应模板: templates/goal_weight.html
- 输出目录: $DATA_DIR/calorie_html/体重目标_<TS>.html
- 占位符: <!--INJECT-DATA--> 恰好 1 次
- 呈现数据: 当前体重/目标值/截止/Δkg/建议速率(自动算截止含推算截止+速率校验,含起始日含起始日+起点体重)

用法:
    python scripts/render_goal_weight.py --mode basic              # 定体重目标
    python scripts/render_goal_weight.py --mode auto_deadline     # 定体重目标(自动算截止)
    python scripts/render_goal_weight.py --mode with_start        # 定体重目标(含起始日)
    python scripts/render_goal_weight.py --mode modify            # 改体重目标
"""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'goal_weight.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa: E402
from weight_goal import get_weight_goal  # noqa: E402


def _latest_weight():
    from db import find_db_path, get_db
    db_path = find_db_path(SKILL_DIR, 'calorie_data.db')
    conn = get_db(db_path)
    row = conn.execute('SELECT weight_kg FROM weight_log ORDER BY date DESC LIMIT 1').fetchone()
    conn.close()
    return row[0] if row else None


def build_data(mode='basic'):
    current = _latest_weight()
    wg = get_weight_goal()
    current_goal = wg[0] if wg else None
    deadline = wg[1] if wg else None
    data = {
        'current_weight': round(current, 1) if current else None,
        'target_weight': current_goal,
        'deadline': deadline,
    }

    if mode == 'basic':
        data['title'] = '定体重目标'
        data['subtitle'] = '目标 kg + 可选截止日期'
        if current is not None and current_goal:
            data['delta_kg'] = round(current - current_goal, 1)
        data['fields'] = [
            {'key': 'weight-goal', 'label': '目标体重', 'unit': 'kg', 'placeholder': '如 70'},
            {'key': 'deadline', 'label': '截止日期', 'unit': '', 'placeholder': '如 2026-12-31(选填)'},
        ]
        data['cliLabel'] = '体重目标 (调用 weight_goal.set_weight_goal):'
        data['extraPrompt'] = '若我未提供目标或档案缺失,请先询问补齐;已明确则直接执行。'

    elif mode == 'auto_deadline':
        data['title'] = '定体重目标(自动算截止)'
        data['subtitle'] = '目标 kg + 期望速率 → 自动推算截止日 + 速率校验'
        # 简单速率校验: 0.25~1.0 kg/周 为合理带
        data['rate_check'] = {'ok': True, 'text': '合理速率带 0.25~1.0 kg/周,超范围会提示'}
        data['fields'] = [
            {'key': 'weight-goal', 'label': '目标体重', 'unit': 'kg', 'placeholder': '如 70'},
            {'key': 'rate', 'label': '期望每周速率', 'unit': 'kg/周', 'placeholder': '如 0.5'},
        ]
        data['cliLabel'] = '体重目标 (调用 weight_goal.set_weight_goal, 截止日由 AI 推算):'
        data['extraPrompt'] = '请按我给的速率推算合理截止日,并校验速率是否在安全范围(0.25~1.0 kg/周)。'

    elif mode == 'with_start':
        data['title'] = '定体重目标(含起始日)'
        data['subtitle'] = '完整 setup: 目标 + 起始日 + 截止日 + 起点体重'
        data['fields'] = [
            {'key': 'weight-goal', 'label': '目标体重', 'unit': 'kg', 'placeholder': '如 70'},
            {'key': 'start-date', 'label': '起始日', 'unit': '', 'placeholder': '如 2026-08-01'},
            {'key': 'deadline', 'label': '截止日期', 'unit': '', 'placeholder': '如 2026-12-31'},
            {'key': 'start-weight', 'label': '起点体重', 'unit': 'kg', 'placeholder': '如 75'},
        ]
        data['cliLabel'] = '体重目标 (调用 weight_goal.set_weight_goal, 含起始日/起点体重):'
        data['extraPrompt'] = '请完整记录起始日与起点体重,作为目标起点。'

    elif mode == 'modify':
        data['title'] = '改体重目标'
        data['subtitle'] = '改目标值或截止日,显示改前/改后 + 新建议速率'
        data['old_goal'] = {'weight_goal': current_goal, 'deadline': deadline}
        data['fields'] = [
            {'key': 'weight-goal', 'label': '新目标体重', 'unit': 'kg', 'placeholder': f'当前 {current_goal}' if current_goal else '如 70'},
            {'key': 'deadline', 'label': '新截止日期', 'unit': '', 'placeholder': f'当前 {deadline}' if deadline else '选填'},
        ]
        data['cliLabel'] = '体重目标 (调用 weight_goal.set_weight_goal):'
        data['extraPrompt'] = '请显示改前/改后,并按新目标给出建议速率。'

    return data


def render_html(data: dict) -> str:
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(f'模板占位符数量异常: {template.count(placeholder)}')
    payload = json.dumps({'status': 'ok', 'data': data, 'message': '体重目标已生成'},
                         ensure_ascii=False).replace('</', '<\\/')
    inject = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace(placeholder, inject, 1)


def main():
    p = argparse.ArgumentParser(description='渲染体重目标 HTML(体重型)')
    p.add_argument('--mode', default='basic',
                   choices=['basic', 'auto_deadline', 'with_start', 'modify'])
    p.add_argument('--output', help='输出文件路径')
    args = p.parse_args()

    try:
        data = build_data(mode=args.mode)
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, '体重目标')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    print(f'✅ {out_path}')
    print(f'   mode={args.mode} · 当前 {data.get("current_weight")} kg → 目标 {data.get("target_weight")} kg')
    return 0


if __name__ == '__main__':
    sys.exit(main())
