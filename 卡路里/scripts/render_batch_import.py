#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_batch_import.py — 批量导入预览 HTML 渲染器

对应 SKILL.md 唤醒词:批量导入食品 / 校验批量导入 / 看食品库（去重）

设计原则:
- 过程型 HTML(AI 协同模式 · 原则 10)
- 必含 3 个复制按钮:采纳 + 修改后复制 + 跳过失败行
- 4 部分 prompt(场景 / 数据 / 期望 / 来源)

数据来源:
  理论上由 batch_import.py 的未来 --json-output 模式产出
  当前用 tests/fixtures/mock/mock_batch_import_data.json 测试

用法:
    python scripts/render_batch_import.py --input tests/fixtures/mock/mock_batch_import_data.json
    python scripts/render_batch_import.py --input <batch_import输出.json> --output /path/out.html
"""

from _base_render import render_template, write_html  # noqa: E402
COMMAND_CN = '批量导入食品'
import argparse
import json
from html_paths import html_path
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'batch_import_preview.html'


def build_parser():
    p = argparse.ArgumentParser(
        prog="render_batch_import",
        description="渲染批量导入预览 HTML(过程型 · AI 协同模式)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument('--input', required=True, help='结构化数据 JSON 文件路径(batch_import 输出 / mock)')
    p.add_argument('--output', help='输出文件路径')
    p.add_argument('--chain', help='AI 思考链注入(meta.chain,不进 UI;复制日志可带出 · R3)')
    p.add_argument('--scene', help='场景名(如 校验批量导入/批量导入食品),默认 批量导入预览')
    return p


def load_data(json_path: Path) -> dict:
    """加载批量导入结构化数据(防御性:类型校验)"""
    if not json_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {json_path}")
    raw = json.loads(json_path.read_text(encoding='utf-8'))

    # BUG #4 修复:防御非 dict 输入(原代码会直接 AttributeError)
    if not isinstance(raw, dict):
        raise ValueError(f"JSON 顶层必须是 dict,实际是 {type(raw).__name__}")

    # 兼容两种格式:
    # 格式 A: { status, data: {summary, runs}, message }  (我们约定的)
    # 格式 B: {summary, runs}                                  (batch_import 未来输出)
    if 'data' in raw and isinstance(raw['data'], dict):
        return raw['data']
    return raw


def normalize(data: dict, chain: str | None = None, scene: str | None = None) -> dict:
    """标准化字段:确保 summary/runs 完整 + 防御性兜底"""
    if not isinstance(data, dict):
        return {'summary': {'total': 0, 'added': 0, 'updated': 0, 'skipped': 0, 'failed': 0, 'jsonl_path': '(空)'}, 'runs': []}

    summary = data.get('summary', {})
    if scene:
        summary['scene'] = scene
    if not isinstance(summary, dict):
        summary = {}
    runs = data.get('runs', [])
    if not isinstance(runs, list):
        runs = []

    # #44 缺陷D修复:batch_import validate 输出 run.name → 模板需要的 product_name
    # (预览明细行按 product_name/brand 渲染;validate 输出只有 name,原样透传会显示「(无名)」)
    # #44 审查(场景 32/33):validate 形态(line/ok|failed/name/reason)统一为模板形态(row/status/product_name)
    is_validate = bool(runs) and all(isinstance(r, dict) and r.get('status') in ('ok', 'failed') for r in runs)
    for r in runs:
        if isinstance(r, dict) and 'product_name' not in r and r.get('name'):
            r['product_name'] = r['name']

    # BUG #1 修复:jsonl_path 兜底,避免 prompt 中出现 "undefined"
    if 'jsonl_path' not in summary:
        summary['jsonl_path'] = summary.get('jsonl_path', 'foods.jsonl')

    if is_validate:
        for r in runs:
            if 'row' not in r and r.get('line') is not None:
                r['row'] = r['line']
            if 'product_name' not in r and r.get('name'):
                r['product_name'] = r['name']
        summary['passed'] = sum(1 for r in runs if r.get('status') == 'ok')
        summary['failed'] = sum(1 for r in runs if r.get('status') == 'failed')
        summary['is_validate'] = True

    # 自动计算缺失字段(防止用户 JSON 不完整)
    if 'total' not in summary:
        summary['total'] = len(runs)
    if 'added' not in summary:
        summary['added'] = sum(1 for r in runs if r.get('status') == 'added')
    if 'updated' not in summary:
        summary['updated'] = sum(1 for r in runs if r.get('status') == 'updated')
    if 'skipped' not in summary:
        summary['skipped'] = sum(1 for r in runs if r.get('status') == 'skipped')
    if 'failed' not in summary:
        summary['failed'] = sum(1 for r in runs if r.get('status') == 'failed')

    # BUG #3 修复:total 与 runs 长度不一致时,标注提示(#44:validate 形态按 通过+失败 计算)
    summary['_data_consistent'] = (
        ((summary.get('passed', summary.get('added', 0)) + summary.get('failed', 0)) == summary['total'])
        if summary.get('is_validate')
        else ((summary['added'] + summary['updated'] +
               summary['skipped'] + summary['failed']) == summary['total'])
    ) and len(runs) == summary['total']

    return {'summary': summary, 'runs': runs, 'meta': {'chain': chain}}


def render_html(data: dict):
    return render_template(TEMPLATE_PATH, data, COMMAND_CN)


def main():
    args = build_parser().parse_args()
    input_path = Path(args.input)

    try:
        raw = load_data(input_path)
        data = normalize(raw, getattr(args, 'chain', None), getattr(args, 'scene', None))
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, f'批量导入预览_{input_path.stem}')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_html(html, out_path)

    s = data['summary']
    print(f'✅ {out_path}')
    print(f'   文件: {s.get("jsonl_path", input_path.name)}')
    print(f'   总数: {s.get("total", 0)} · 新增 {s.get("added", 0)} · 更新 {s.get("updated", 0)} · 跳过 {s.get("skipped", 0)} · 失败 {s.get("failed", 0)}')
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())