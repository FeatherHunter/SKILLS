#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_process_progress.py — 4 步流程进度可视化 HTML 渲染器

对应 SKILL.md 唤醒词:落地健身计划 / 卡路里同步 / 回写训记 / 训记-覆盖X日

设计原则:
- 过程型 HTML(AI 协同模式 · 原则 10 · 复制"从哪步继续" prompt)
- 3 个复制按钮:继续指令(从失败步骤)/ 采纳现状 / 完整日志
- 4 部分 prompt:场景 + 已完成/失败/待办 + 期望重试 + 来源

数据源:
  理论上由 sync_plan.py / 落地健身计划 / 训记覆盖等 4 步流程的 --json-output
  当前用 mock_process_progress.json 测试

用法:
    python scripts/render_process_progress.py --input mock_process_progress.json
    python scripts/render_process_progress.py --input <流程输出.json> --output /path/out.html
"""
import argparse
import json
from html_paths import html_path
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'process_progress.html'


def build_parser():
    p = argparse.ArgumentParser(
        prog="render_process_progress",
        description="渲染 4 步流程进度 HTML(过程型 · AI 协同模式)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument('--input', required=True, help='流程结构化数据 JSON 文件路径')
    p.add_argument('--output', help='输出文件路径')
    return p


def load_data(json_path: Path) -> dict:
    """加载流程数据(防御性:类型校验)"""
    if not json_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {json_path}")
    raw = json.loads(json_path.read_text(encoding='utf-8'))

    if not isinstance(raw, dict):
        raise ValueError(f"JSON 顶层必须是 dict,实际是 {type(raw).__name__}")

    # 兼容格式 A/B
    if 'data' in raw and isinstance(raw['data'], dict):
        return raw['data']
    return raw


def normalize(data: dict) -> dict:
    """标准化字段 + 自动计算 summary(防止 mock 漏字段)"""
    if not isinstance(data, dict):
        return {'summary': default_summary(), 'steps': []}

    summary = data.get('summary', {})
    if not isinstance(summary, dict):
        summary = {}
    steps = data.get('steps', [])
    if not isinstance(steps, list):
        steps = []

    # 兜底
    if 'process_name' not in summary:
        summary['process_name'] = summary.get('process_name', '(未命名流程)')

    # 自动统计各状态步数
    if 'total_steps' not in summary:
        summary['total_steps'] = len(steps)
    if 'completed_steps' not in summary:
        summary['completed_steps'] = sum(1 for s in steps if s.get('status') == 'done')
    if 'failed_steps' not in summary:
        summary['failed_steps'] = sum(1 for s in steps if s.get('status') == 'failed')
    # BUG #2 修复:补充 pending_steps(数据契约完整性)
    if 'pending_steps' not in summary:
        summary['pending_steps'] = sum(1 for s in steps if (s.get('status') or 'pending') == 'pending')

    return {'summary': summary, 'steps': steps}


def default_summary() -> dict:
    return {
        'process_name': '(空)',
        'process_type': '',
        'total_steps': 0,
        'completed_steps': 0,
        'failed_steps': 0,
        'pending_steps': 0,
    }


def render_html(data: dict) -> str:
    """读模板 + 注入数据"""
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(f"模板占位符数量异常: {template.count(placeholder)}")

    payload = json.dumps({'status': 'ok', 'data': data, 'message': '流程进度已生成'},
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

    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, f'process_progress_{input_path.stem}')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')

    s = data['summary']
    print(f'✅ {out_path}')
    print(f'   流程: {s.get("process_name", "?")}')
    print(f'   总步骤: {s.get("total_steps", 0)} · 完成 {s.get("completed_steps", 0)} · 失败 {s.get("failed_steps", 0)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())