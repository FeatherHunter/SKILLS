#!/usr/bin/env python3
"""复盘训练 CLI — 计划 vs 实绩对比（2026-07-23 D2 重构：加 --format json）

使用方法：
    python3 exercise_review.py --today
    python3 exercise_review.py --yesterday
    python3 exercise_review.py --days 7
    python3 exercise_review.py --start 2026-07-13 --end 2026-07-19
    python3 exercise_review.py --days 7 --format json    # 机器可读
"""
import sys
import argparse
import json
from datetime import date, timedelta

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from analysis import exercise_analysis


def parse_args():
    parser = argparse.ArgumentParser(description="复盘训练 — 计划 vs 实绩对比")
    parser.add_argument('--start', help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--today', action='store_true', help='今日 (start=end=today)')
    parser.add_argument('--yesterday', action='store_true', help='昨日 (start=end=yesterday)')
    parser.add_argument('--day-before-yesterday', action='store_true', help='前日 (start=end=today-2)')
    parser.add_argument('--days', type=int, help='最近 N 天 (start=today-N+1, end=today)')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                        help='输出格式:text(默认·人类可读) / json(机器可读)')
    return parser.parse_args()


def resolve_range(args):
    """解析参数 → (start, end)。糖参数优先级: --today > --yesterday > --day-before-yesterday > --days > --start/--end"""
    today = date.today()
    if args.today:
        return today.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
    if args.yesterday:
        y = today - timedelta(days=1)
        return y.strftime('%Y-%m-%d'), y.strftime('%Y-%m-%d')
    if args.day_before_yesterday:
        d = today - timedelta(days=2)
        return d.strftime('%Y-%m-%d'), d.strftime('%Y-%m-%d')
    if args.days is not None:
        start = today - timedelta(days=args.days - 1)
        return start.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
    if args.start and args.end:
        return args.start, args.end
    if args.start:
        return args.start, args.start
    return today.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')


def main():
    args = parse_args()
    start, end = resolve_range(args)

    if args.format == 'json':
        # 2026-07-23 D2：调 analysis 函数 + as_dict=True
        result = exercise_analysis(start, end, 'review', as_dict=True, silent=True)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # text 模式（默认）
    print(f"📅 复盘范围: {start} ~ {end}\n")
    try:
        exercise_analysis(start, end, 'review')
    except ValueError as e:
        print(f"❌ 日期格式错: {e}\n请用 YYYY-MM-DD 格式,如 2026-07-13")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 复盘失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()