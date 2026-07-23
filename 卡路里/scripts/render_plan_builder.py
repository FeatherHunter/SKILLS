#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_plan_builder.py — 健身计划预览 wizard HTML 渲染器

对应 SKILL.md 唤醒词:制定健身计划 / 改健身计划

设计原则:
- 过程型 HTML(AI 协同模式 · 原则 10)
- 3 个复制按钮:采纳 / 修改偏好 / 换某动作
- 4 部分 prompt:场景 + 数据 + 期望 + 来源
- Apple 风 + 部位色板(7 色 push/pull/legs 分组,延续 workout_plan)

用法:
    python scripts/render_plan_builder.py --mock mock_plan_builder.json
    python scripts/render_plan_builder.py --mock <plan.json> --output /path/out.html
"""
import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'plan_builder_wizard.html'


def build_parser():
    p = argparse.ArgumentParser(
        prog='render_plan_builder',
        description='渲染健身计划预览 wizard(过程型 · AI 协同)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument('--mock', required=True,
                   help='plan JSON 文件路径(mock 或 plan_generator 输出)')
    p.add_argument('--output', help='输出文件路径')
    return p


def load_data(json_path: Path) -> dict:
    """加载 plan JSON(防御性)"""
    if not json_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {json_path}")
    raw = json.loads(json_path.read_text(encoding='utf-8'))

    if not isinstance(raw, dict):
        raise ValueError(f"JSON 顶层必须是 dict,实际是 {type(raw).__name__}")

    # 兼容 {data: ...} 或裸 plan
    if 'data' in raw and isinstance(raw['data'], dict):
        return raw['data']
    return raw


def normalize(data: dict) -> dict:
    """标准化字段(缺失自动补)"""
    if not isinstance(data, dict):
        return default_plan()

    # summary
    summary = data.get('summary', {})
    if not isinstance(summary, dict):
        summary = {}
    prefs = data.get('preferences', {})
    if not isinstance(prefs, dict):
        prefs = {}
    weeks = data.get('weeks', [])
    if not isinstance(weeks, list):
        weeks = []

    # 兜底计算
    if 'total_sessions' not in summary:
        summary['total_sessions'] = sum(
            1 for w in weeks for d in w.get('days', []) for s in d.get('sessions', [])
        )
    if 'total_sets' not in summary:
        summary['total_sets'] = sum(
            s.get('total_sets', 0) for w in weeks for d in w.get('days', []) for s in d.get('sessions', [])
        )

    return {'summary': summary, 'preferences': prefs, 'weeks': weeks}


def default_plan() -> dict:
    return {
        'summary': {'plan_title': '(空)', 'total_weeks': 0, 'total_sessions': 0, 'total_sets': 0},
        'preferences': {},
        'weeks': [],
    }


def render_html(data: dict) -> str:
    """读模板 + 注入数据"""
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(f"模板占位符数量异常: {template.count(placeholder)}")

    payload = json.dumps({'status': 'ok', 'data': data, 'message': '健身计划预览已生成'},
                         ensure_ascii=False).replace('</', '<\\/')
    inject = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace(placeholder, inject, 1)


def main():
    args = build_parser().parse_args()
    input_path = Path(args.mock)

    try:
        raw = load_data(input_path)
        data = normalize(raw)
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    default_name = f'plan_builder_{input_path.stem}.html'
    out_path = Path(args.output) if args.output else Path('/tmp') / default_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')

    s = data['summary']
    print(f'✅ {out_path}')
    print(f'   计划: {s.get("plan_title", "?")} · {s.get("total_weeks", 0)} 周 · {s.get("total_sessions", 0)} 场')
    return 0


if __name__ == '__main__':
    sys.exit(main())