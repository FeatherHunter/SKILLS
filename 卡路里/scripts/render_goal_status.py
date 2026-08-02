#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_goal_status.py — 目标状态 HTML 渲染器(状态型)

对应 SKILL.md 唤醒词: 暂停所有目标 / 重启所有目标
对应模板: templates/goal_status.html
- 输出目录: $DATA_DIR/calorie_html/目标状态_<TS>.html
- 占位符: <!--INJECT-DATA--> 恰好 1 次
- 呈现数据: 暂停状态 + 说明(记录照常,仅目标暂停)+ 恢复入口提示 / 重启状态

用法:
    python scripts/render_goal_status.py --status paused    # 暂停所有目标
    python scripts/render_goal_status.py --status resumed  # 重启所有目标
"""
import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'goal_status.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa: E402
import goal_manager  # noqa: E402
from render_goal_common import build_meta, chain_valid, scene_path  # noqa: E402


def build_data(status='paused'):
    if status == 'paused':
        r = goal_manager.pause_all_goals()
        return {
            'title': '暂停所有目标',
            'subtitle': '临时冻结全部目标',
            'timeHint': f"时间 {r['updated_at']}",
            'paused': True,
            'note': r['note'],
            'restoreHint': r['restore_hint'],
            'receipt': f"id={r['id']} | 日期 {r['updated_at']} | 影响 {r['rows_affected']} 行",
        }
    else:
        r = goal_manager.resume_all_goals()
        return {
            'title': '重启所有目标',
            'subtitle': '从暂停恢复全部目标',
            'timeHint': f"时间 {r['updated_at']}",
            'paused': False,
            'receipt': f"id={r['id']} | 日期 {r['updated_at']} | 影响 {r['rows_affected']} 行 · {r['resume_state']}",
        }


def render_html(data: dict) -> str:
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(f'模板占位符数量异常: {template.count(placeholder)}')
    payload = json.dumps({'status': 'ok', 'data': data, 'message': '目标状态已生成'},
                         ensure_ascii=False).replace('</', '<\\/')
    inject = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace(placeholder, inject, 1)


def main():
    p = argparse.ArgumentParser(description='渲染目标状态 HTML(状态型)')
    p.add_argument('--status', default='paused', choices=['paused', 'resumed'])
    p.add_argument('--chain', help='AI 思考链(必填·强制规则:未传=AI 未按 SKILL.md 流程执行 · 2026-08-02)')
    p.add_argument('--output', help='输出文件路径')
    args = p.parse_args()

    # R3 思考链强制(live 模式必传)
    if not chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        print('   未传 = AI 未按 SKILL.md 流程执行,行为不可控。', file=sys.stderr)
        print('   请传入你的实际处理步骤,例如:', file=sys.stderr)
        print('     --chain "1.识别唤醒词→2.调goal_manager→3.生成回执"', file=sys.stderr)
        return 2

    # R4 自描述:场景名推断
    scene_name = '暂停所有目标' if args.status == 'paused' else '重启所有目标'
    output_type = 'receipt'

    try:
        data = build_data(status=args.status)
        # R1 视图分离:meta 不进 UI(复制日志带出)
        data['meta'] = build_meta(
            wake_word=scene_name,
            source='daily_goal.goal_paused(goal_manager)',
            chain=args.chain,
        )
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    # R5 命名:<场景名>_<类型中文>_<TS>.html
    out_path = Path(args.output) if args.output else scene_path(scene_name, output_type)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    print(f'✅ {out_path}')
    print(f'   status={args.status} · {"已暂停" if data["paused"] else "已恢复"}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
