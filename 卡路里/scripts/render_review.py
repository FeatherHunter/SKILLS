#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_review.py — 渲染复盘 HTML 报告

对应 SKILL.md 唤醒词:`复盘 / 复盘今日 / 复盘本周 / 复盘本月 / 复盘本年 / 复盘日期范围`

设计原则(《预置 HTML + 注入数据指导手册》):
- 复用 review_cli.py gen 已经生成的 enriched 数据(避免重复 SQL)
- 占位符唯一:<!--INJECT-DATA--> 恰好 1 次
- 输出到新文件,原 templates/review_template.html 不变

用法:
    python scripts/render_review.py                                # 默认本周复盘
    python scripts/render_review.py --range 2026-07-13:2026-07-19   # 自定义范围
    python scripts/render_review.py --type month                    # 本月
    python scripts/render_review.py --output <path>                # 指定输出
"""
import argparse
import json
from html_paths import html_path
import subprocess
import sys
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'review_template.html'


def build_parser():
    p = argparse.ArgumentParser(
        prog="render_review",
        description="渲染复盘 HTML 报告 v2(8 dim 卡片 + 体重 SVG + 异常天)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--range", help="日期范围,如 2026-07-13:2026-07-19")
    p.add_argument("--type", choices=["day", "week", "month", "year"], default="week",
                   help="时间类型(默认 week)")
    p.add_argument("--output", help="输出文件路径")
    return p


def fetch_gen(args) -> dict:
    """调 review_cli.py gen 拿 JSON(跳过 leading 文本行)"""
    cmd = ['python3', str(SCRIPT_DIR / 'review_cli.py'), 'gen']
    if args.range:
        cmd.extend(['--range', args.range])
    else:
        cmd.extend(['--type', args.type])

    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    if result.returncode != 0:
        raise RuntimeError(
            f"review_cli.py gen 失败 (exit={result.returncode})\n"
            f"stderr: {result.stderr}"
        )

    # 跳过 leading 非 JSON 行(以 "→ " 开头的提示)
    out = result.stdout
    json_start = out.find('{')
    if json_start == -1:
        raise ValueError(f"找不到 JSON 起始位置:\n{out[:200]}")
    json_str = out[json_start:]
    return json.loads(json_str)


def render_html(gen_result: dict) -> str:
    """读 enriched 数据文件 + 注入模板"""
    template = TEMPLATE_PATH.read_text(encoding='utf-8')

    # 占位符唯一性
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(
            f"模板占位符数量异常: 期望 1 个,实际 {template.count(placeholder)} 个"
        )

    # 读 enriched 真实数据(从 data_path)
    data_path = gen_result['data']['data_path']
    enriched = json.loads(Path(data_path).read_text(encoding='utf-8'))['enriched']

    # 包装成 {status, data, message} 三段式
    payload_obj = {
        'status': gen_result.get('status', 'ok'),
        'data': enriched,
        'message': gen_result.get('message', '已生成'),
    }

    # 转义 </ 防止提前闭合 script 标签
    payload = json.dumps(payload_obj, ensure_ascii=False).replace('</', '<\\/')
    inject = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace(placeholder, inject, 1)


def main():
    args = build_parser().parse_args()

    try:
        gen_result = fetch_gen(args)
        html = render_html(gen_result)
    except Exception as e:
        print(f"❌ 渲染失败: {e}", file=sys.stderr)
        return 1

    # 输出
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = html_path(SKILL_DIR, 'review')

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')

    # 摘要
    e = json.loads(Path(gen_result['data']['data_path']).read_text(encoding='utf-8'))['enriched']
    print(f"✅ {out_path}")
    print(f"   类型: {e['range'].get('type', 'custom')} | 范围: {e['range']['start']} ~ {e['range']['end']}")
    print(f"   完整日: {e['complete_days_count']} | 异常天: {len(e.get('anomaly_days', []))} 条")
    print(f"   TDEE: {e['tdee']} 卡/天 | 周缺口: {e['weekly_deficit']} 卡")
    return 0


if __name__ == "__main__":
    sys.exit(main())