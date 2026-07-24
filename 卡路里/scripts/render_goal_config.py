#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_goal_config.py — 目标配置 HTML 渲染器(G6)

对应 SKILL.md 唤醒词:设营养目标 / 查营养目标 / 设体重目标 / 查体重目标

设计原则(与 G2-G5 一致):
- 过程型 HTML(AI 协同模式 · 原则 10)
- 3 个复制按钮:采纳全部 / 仅营养 / 仅体重
- 4 部分 prompt:场景 + 数据 + 期望 + 来源
- Apple 风:系统字体 / 浅灰底 / 主色蓝

用法:
    python scripts/render_goal_config.py --mock mock_goal_config.json
    python scripts/render_goal_config.py --mock <JSON> --output /path/out.html
"""
import argparse
import json
from html_paths import html_path
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'goal_config.html'


def build_parser():
    p = argparse.ArgumentParser(
        prog='render_goal_config',
        description='渲染目标配置 HTML(G6 · 5 个 slider + mini chart)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument('--mock', required=True, help='目标配置 JSON 文件路径(mock 或真实数据)')
    p.add_argument('--output', help='输出文件路径')
    return p


def load_data(json_path: Path) -> dict:
    if not json_path.exists():
        raise FileNotFoundError(f'输入文件不存在: {json_path}')
    raw = json.loads(json_path.read_text(encoding='utf-8'))
    if not isinstance(raw, dict):
        raise ValueError(f'JSON 顶层必须是 dict,实际是 {type(raw).__name__}')
    if 'data' in raw and isinstance(raw['data'], dict):
        return raw['data']
    return raw


def normalize(data: dict) -> dict:
    """标准化字段(防御性补全)"""
    if not isinstance(data, dict):
        return {'current_goal': {}, 'yesterday_actual': {}, 'weight_progress': None}
    return {
        'current_goal': data.get('current_goal', {}) if isinstance(data.get('current_goal'), dict) else {},
        'yesterday_actual': data.get('yesterday_actual', {}) if isinstance(data.get('yesterday_actual'), dict) else {},
        'weight_progress': data.get('weight_progress') if isinstance(data.get('weight_progress'), dict) else None,
    }


def render_html(data: dict) -> str:
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(f'模板占位符数量异常: {template.count(placeholder)}')

    payload = json.dumps({'status': 'ok', 'data': data, 'message': '目标配置已生成'},
                         ensure_ascii=False).replace('</', '<\\/')
    inject = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace(placeholder, inject, 1)


def main():
    args = build_parser().parse_args()
    input_path = Path(args.mock)

    try:
        data = normalize(load_data(input_path))
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, f'goal_config_{input_path.stem}')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')

    cg = data.get('current_goal', {})
    print(f'✅ {out_path}')
    print(f'   目标: 卡 {cg.get("calorie_goal", "?")} / 蛋白 {cg.get("protein_goal", "?")}g / 碳水 {cg.get("carbs_goal", "?")}g / 脂肪 {cg.get("fat_goal", "?")}g / 水 {cg.get("water_goal", "?")}ml')
    wp = data.get('weight_progress')
    if wp:
        print(f'   体重: 当前 {wp.get("current", "?")}kg → 目标 {wp.get("target", "?")}kg ({wp.get("days_left", "?")}天)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
