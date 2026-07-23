#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_batch_import.py — 批量导入预览 HTML 渲染器

对应 SKILL.md 唤醒词:批量导入 / 校验批量 / 查食品库去重

设计原则:
- 过程型 HTML(AI 协同模式 · 原则 10)
- 必含 3 个复制按钮:采纳 + 修改后复制 + 跳过失败行
- 4 部分 prompt(场景 / 数据 / 期望 / 来源)

数据来源:
  理论上由 batch_import.py 的未来 --json-output 模式产出
  当前用 mock_batch_import_data.json 测试

用法:
    python scripts/render_batch_import.py --input mock_batch_import_data.json
    python scripts/render_batch_import.py --input <batch_import输出.json> --output /path/out.html
"""
import argparse
import json
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
    return p


def load_data(json_path: Path) -> dict:
    """加载批量导入结构化数据"""
    if not json_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {json_path}")
    raw = json.loads(json_path.read_text(encoding='utf-8'))

    # 兼容两种格式:
    # 格式 A: { status, data: {summary, runs}, message }  (我们约定的)
    # 格式 B: {summary, runs}                                  (batch_import 未来输出)
    if 'data' in raw:
        return raw['data']
    return raw


def normalize(data: dict) -> dict:
    """标准化字段:确保 summary/runs 完整"""
    summary = data.get('summary', {})
    runs = data.get('runs', [])

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

    return {'summary': summary, 'runs': runs}


def render_html(data: dict) -> str:
    """读模板 + 注入数据"""
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(f"模板占位符数量异常: {template.count(placeholder)}")

    payload = json.dumps({'status': 'ok', 'data': data, 'message': '批量导入预览已生成'},
                         ensure_ascii=False).replace('</', '<\\/')
    inject = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace(placeholder, inject, 1)


def main():
    args = build_parser().parse_args()
    input_path = Path(args.input)

    try:
        raw = load_data(input_path)
        data = normalize(raw)
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    default_name = f'batch_import_preview_{input_path.stem}.html'
    out_path = Path(args.output) if args.output else Path('/tmp') / default_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')

    s = data['summary']
    print(f'✅ {out_path}')
    print(f'   文件: {s.get("jsonl_path", input_path.name)}')
    print(f'   总数: {s.get("total", 0)} · 新增 {s.get("added", 0)} · 更新 {s.get("updated", 0)} · 跳过 {s.get("skipped", 0)} · 失败 {s.get("failed", 0)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())