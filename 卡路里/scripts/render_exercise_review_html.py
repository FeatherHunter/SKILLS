#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_exercise_review_html.py — 渲染训练复盘 HTML

对应 SKILL.md 唤醒词:`复盘训练`（HTML 可视化版）

设计:7 天完成率热力图 + 每日明细表 + 异常天高亮
模板:templates/exercise_review.html
数据源:exercise_review.py --format json(由本渲染器 subprocess 调用)

用法:
    python scripts/render_exercise_review_html.py                  # 默认 7 天
    python scripts/render_exercise_review_html.py --days 14       # 14 天
    python scripts/render_exercise_review_html.py --start X --end Y
    python scripts/render_exercise_review_html.py --output <path>
"""
import argparse
import json
from html_paths import html_path
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'exercise_review.html'


def build_parser():
    p = argparse.ArgumentParser(
        prog="render_exercise_review_html",
        description="渲染训练复盘 HTML(完成率热力图 + 异常高亮)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--start", help="开始日期 YYYY-MM-DD")
    p.add_argument("--end", help="结束日期 YYYY-MM-DD")
    p.add_argument("--days", type=int, help="最近 N 天(默认 7)")
    p.add_argument("--output", help="输出文件路径")
    return p


def fetch_json(start: str, end: str) -> dict:
    """调 exercise_review.py --format json 拿数据"""
    result = subprocess.run(
        ['python3', str(SCRIPT_DIR / 'exercise_review.py'),
         '--start', start, '--end', end, '--format', 'json'],
        capture_output=True, text=True, encoding='utf-8',
    )
    if result.returncode != 0:
        raise RuntimeError(f"exercise_review.py 失败 (exit={result.returncode})\n{result.stderr}")
    return json.loads(result.stdout)


def render_html(data: dict) -> str:
    """读模板 + 注入"""
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(f"模板占位符数量异常: {template.count(placeholder)}")

    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    inject = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace(placeholder, inject, 1)


def main():
    args = build_parser().parse_args()

    if args.start and args.end:
        start, end = args.start, args.end
    elif args.start:
        start = end = args.start
    else:
        days = args.days or 7
        end = date.today().isoformat()
        start = (date.today() - timedelta(days=days - 1)).isoformat()

    try:
        data = fetch_json(start, end)
        html = render_html(data)
    except Exception as e:
        print(f"❌ 渲染失败: {e}", file=sys.stderr)
        return 1

    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, 'exercise_review')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')

    d = data.get('data', {})
    days_count = len(d)
    train_days = sum(1 for v in d.values() if not v.get('is_rest_day'))
    print(f"✅ {out_path}")
    print(f"   范围: {start} ~ {end} | 训练 {train_days}/{days_count} 天")
    return 0


if __name__ == "__main__":
    sys.exit(main())