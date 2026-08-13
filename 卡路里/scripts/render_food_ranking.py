#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_food_ranking.py — 渲染食物排行榜 HTML（1 渲染器 5 榜单）

对应 SKILL.md 唤醒词: 看高热量榜 / 看低热量榜 / 看频繁吃榜 / 看高碳水榜 / 看高蛋白榜 / 看高热量榜（最近 30 天）/ 看高热量榜（本月）/ 看高热量榜（自定义）

设计:1 个渲染器服务 5 个榜单(category 参数切换)
模板:templates/food_ranking.html
数据源:analysis.diet_food_ranking(as_dict=True) × 5

用法:
    python scripts/render_food_ranking.py                                # 默认高热量榜
    python scripts/render_food_ranking.py --category low_calorie         # 切换榜单
    python scripts/render_food_ranking.py --range 7/13:7/19              # 自定义范围
    python scripts/render_food_ranking.py --all --output <path>          # 一次性出 5 榜单
"""

from _base_render import render_template, write_html  # noqa: E402
COMMAND_CN = '看食品榜单'
import argparse
import json
from html_paths import html_path
from _cmd_maps import FOOD_RANKING_CATEGORY_MAP
import sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'food_ranking.html'

CATEGORIES = ('high_calorie', 'low_calorie', 'frequent', 'high_carb', 'high_protein')


def build_parser():
    p = argparse.ArgumentParser(
        prog="render_food_ranking",
        description="渲染食物排行榜 HTML(1 模板 5 榜单)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--category", choices=CATEGORIES, default='high_calorie',
                   help="榜单类别(默认 high_calorie)")
    p.add_argument("--all", action="store_true", help="一次性出 5 个榜单(注入同一文件)")
    p.add_argument("--start", help="开始日期 YYYY-MM-DD")
    p.add_argument("--end", help="结束日期 YYYY-MM-DD")
    p.add_argument("--days", type=int, help="最近 N 天(默认 7)")
    p.add_argument("--top-n", type=int, default=5, help="每个榜单取前 N 名(默认 5)")
    p.add_argument("--output", help="输出文件路径")
    p.add_argument("--chain", help="AI 思考链注入(顶层 meta.chain,不进 UI;复制日志可带出 · R3)")
    return p


def fetch_one_ranking(category: str, start: str, end: str, top_n: int) -> dict:
    """调 analysis.diet_food_ranking(as_dict=True) 拿单个榜单"""
    sys.path.insert(0, str(SCRIPT_DIR))
    from analysis.diet import diet_food_ranking
    return diet_food_ranking(start, end, category=category, top_n=top_n, as_dict=True)


def render_html(data: dict):
    return render_template(TEMPLATE_PATH, data, COMMAND_CN)


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

    # 决定要拉的榜单
    if args.all:
        cats = CATEGORIES
    else:
        cats = (args.category,)

    # 拉数据
    try:
        data = {}
        for cat in cats:
            # #44:拍平契约——模板读 DATA[cat].items(渲染器返回 {status, data:{...}} 嵌套)
            res = fetch_one_ranking(cat, start, end, args.top_n)
            data[cat] = res.get('data', res) if isinstance(res, dict) else res
        if args.chain:
            data['meta'] = {'chain': args.chain, 'start': start, 'end': end}
        html = render_html(data)
    except Exception as e:
        print(f"❌ 渲染失败: {e}", file=sys.stderr)
        return 1

    # 输出
    if args.output:
        out_path = Path(args.output)
    elif args.all:
        out_path = html_path(SKILL_DIR, '食物排行_全部')
    else:
        out_path = html_path(SKILL_DIR, f'食物排行_{FOOD_RANKING_CATEGORY_MAP[args.category]}')

    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_html(html, out_path)

    print(f"✅ {out_path}")
    print(f"   范围: {start} ~ {end} | 榜单: {', '.join(cats)}")
    for cat in cats:
        items = data[cat].get('data', {}).get('items', [])
        if items:
            print(f"   {cat:15} TOP{len(items)}: {items[0]['food_name']} ({items[0]['total_cal']}卡)")
    return 0


if __name__ == "__main__":
    from _io_guard import guard_io; guard_io()
    sys.exit(main())