#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_health_dashboard.py — 渲染健康仪表盘 HTML

对应 SKILL.md 唤醒词:`查健康报告`

数据源:analysis.dashboard(as_dict=True)
模板:templates/health_dashboard.html

用法:
    python scripts/render_health_dashboard.py                    # 默认本周
    python scripts/render_health_dashboard.py --range 7/13:7/19 # 自定义
    python scripts/render_health_dashboard.py --output <path>   # 指定输出
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
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'health_dashboard.html'


def build_parser():
    p = argparse.ArgumentParser(
        prog="render_health_dashboard",
        description="渲染健康仪表盘 HTML(4 维 KPI + 异常提醒)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--start", help="开始日期 YYYY-MM-DD")
    p.add_argument("--end", help="结束日期 YYYY-MM-DD")
    p.add_argument("--days", type=int, help="最近 N 天(默认 7)")
    p.add_argument("--output", help="输出文件路径")
    return p


def fetch_dashboard(start: str, end: str) -> dict:
    """调 analysis.dashboard(as_dict=True)"""
    sys.path.insert(0, str(SCRIPT_DIR))
    from analysis import dashboard
    return dashboard(start, end, as_dict=True)


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

    # 解析日期范围
    if args.start and args.end:
        start, end = args.start, args.end
    elif args.start:
        start = end = args.start
    else:
        days = args.days or 7
        end = date.today().isoformat()
        start = (date.today() - timedelta(days=days - 1)).isoformat()

    try:
        data = fetch_dashboard(start, end)
        html = render_html(data)
    except Exception as e:
        print(f"❌ 渲染失败: {e}", file=sys.stderr)
        return 1

    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, 'health_dashboard')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')

    d = data.get('data', {})
    print(f"✅ {out_path}")
    print(f"   范围: {start} ~ {end} | status={data.get('status')}")
    print(f"   摄入: {d.get('calorie', {}).get('avg_cal', '?')} 卡/天")
    print(f"   运动: {d.get('exercise', {}).get('days_with_exercise', '?')} 天")
    print(f"   体重: {d.get('weight', {}).get('avg_weight', '?')} kg ({d.get('weight', {}).get('trend', '?')})")
    print(f"   缺口: {d.get('deficit', {}).get('avg_deficit', '?')} 卡/天")
    return 0


if __name__ == "__main__":
    sys.exit(main())