#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_weight_receipt.py — 记体重回执 HTML 渲染器(G7)

对应 SKILL.md 唤醒词:记体重

设计原则(回执型 C,非过程型 B):
- 录入后立即看到大数字 + 趋势图 + 复制按钮
- 无 AI 互动(数据已写入数据库)
- Apple 风 + 趋势图 + 新点高亮

用法:
    python scripts/render_weight_receipt.py --mock mock_weight_receipt.json
    python scripts/render_weight_receipt.py --mock <JSON> --output /path/out.html
"""
import argparse
import json
from html_paths import html_path
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'weight_log_receipt.html'


def build_parser():
    p = argparse.ArgumentParser(
        prog='render_weight_receipt',
        description='渲染记体重回执 HTML(G7 · 趋势图 + 大数字回执)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument('--mock', required=True, help='回执数据 JSON 文件路径(mock 或 weight.py 输出)')
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
    if not isinstance(data, dict):
        return {'summary': {}, 'history': []}
    return {
        'summary': data.get('summary', {}) if isinstance(data.get('summary'), dict) else {},
        'history': data.get('history', []) if isinstance(data.get('history'), list) else [],
    }


def render_html(data: dict) -> str:
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(f'模板占位符数量异常: {template.count(placeholder)}')

    payload = json.dumps({'status': 'ok', 'data': data, 'message': '记体重回执已生成'},
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

    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, f'weight_log_receipt_{input_path.stem}')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')

    r = data.get('summary', {}).get('new_record', {})
    print(f'✅ {out_path}')
    print(f'   已记录: {r.get("date", "?")} {r.get("time", "")} | {r.get("weight_kg", "?")}kg | BMI {r.get("bmi", "?")}')
    print(f'   趋势: {len(data.get("history", []))} 条历史')
    return 0


if __name__ == '__main__':
    sys.exit(main())
