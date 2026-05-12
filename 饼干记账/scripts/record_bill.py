#!/usr/bin/env python3
"""
饼干记账 CLI v2.0（模块化重构版）

使用方法：
    python3 record_bill.py add --category 餐饮 --amount -35
    python3 record_bill.py list
    python3 record_bill.py list --date 2026-05-01
    python3 record_bill.py list --from 2026-05-01 --to 2026-05-10
    python3 record_bill.py list --category 餐饮
    python3 record_bill.py search "单车"
    python3 record_bill.py summary
    python3 record_bill.py monthly --month 2026-05
    python3 record_bill.py compare
    python3 record_bill.py recent --limit 10
"""

import sys
from datetime import datetime
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent.resolve()
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from db import add_bill
from query import (
    list_today, list_date, list_date_range,
    list_by_category, search_keyword, list_recent
)
from analyze import (
    get_today_summary, monthly_summary,
    compare_periods, get_category_breakdown
)


def _format_record(r: dict) -> str:
    """格式化单条记录"""
    return f"{r['time']} | {r['category']} | {r['amount']:.2f} | {r.get('note', '')}"


def cmd_add(args):
    """添加账单"""
    time_str = args.time or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    result = add_bill(
        category=args.category,
        amount=args.amount,
        time_str=time_str,
        account=args.account or "",
        ledger=args.ledger or "生活",
        currency=args.currency or "人民币",
        note=args.note or ""
    )
    print(f"✓ 已记录：{result['category']} {result['amount']:.2f}")
    return result


def cmd_list(args):
    """查询记录"""
    records = []

    if args.date:
        records = list_date(args.date)
    elif args.from_date and args.to_date:
        records = list_date_range(args.from_date, args.to_date)
    elif args.from_date or args.to_date:
        print("错误：--from 和 --to 必须同时指定")
        return
    elif args.category:
        records = list_by_category(args.category)
    else:
        records = list_today()

    if not records:
        print("(无记录)")
        return

    for r in records:
        print(_format_record(r))


def cmd_search(args):
    """搜索备注关键词"""
    records = search_keyword(args.keyword)
    if not records:
        print(f"(无匹配 '{args.keyword}' 的记录)")
        return
    print(f"=== 搜索结果: '{args.keyword}' ({len(records)}条) ===")
    for r in records:
        print(_format_record(r))


def cmd_summary(args):
    """今日摘要"""
    result = get_today_summary()
    print(f"今日 {result['date']}")
    print(f"记录数: {result['count']}")
    print(f"支出: {result['expense']:.2f}")
    print(f"收入: {result['income']:.2f}")
    print(f"净额: {result['net']:.2f}")


def cmd_monthly(args):
    """月度汇总"""
    result = monthly_summary(args.month)
    print(f"=== {args.month} 月度汇总 ===")
    print(f"支出: {result['expense']:.2f}")
    print(f"收入: {result['income']:.2f}")
    print(f"净额: {result['net']:.2f}")
    if result['categories']:
        print("\n分类明细:")
        for c in result['categories']:
            print(f"  {c['category']}: {c['total']:.2f} ({c['count']}笔)")


def cmd_compare(args):
    """周期对比"""
    period = args.period or "week"
    result = compare_periods(period)

    if "error" in result:
        print(result["error"])
        return

    label = "周" if period == "week" else "月"
    print(f"=== {label}度对比 ===\n")
    print(f"{result['this']['label']}")
    print(f"  支出: {result['this']['expense']:.2f}")
    print(f"  收入: {result['this']['income']:.2f}")
    print(f"  净额: {result['this']['net']:.2f}")
    print(f"\n{result['last']['label']}")
    print(f"  支出: {result['last']['expense']:.2f}")
    print(f"  收入: {result['last']['income']:.2f}")
    print(f"  净额: {result['last']['net']:.2f}")
    print(f"\n变化:")
    change = result['change']
    diff = change['expense_diff']
    pct = change['expense_pct']
    direction = "↑" if diff > 0 else "↓" if diff < 0 else "→"
    print(f"  支出 {direction} {abs(diff):.2f} ({abs(pct):.1f}%)")


def cmd_recent(args):
    """最近N条"""
    limit = args.limit or 10
    records = list_recent(limit)
    if not records:
        print("(无记录)")
        return
    print(f"=== 最近 {len(records)} 条 ===")
    for r in records:
        print(_format_record(r))


def cmd_breakdown(args):
    """分类明细"""
    from_date = args.from_date
    to_date = args.to_date
    result = get_category_breakdown(from_date, to_date)

    print(f"=== 分类支出明细 ===")
    if from_date or to_date:
        print(f"期间: {result['from']} ~ {result['to']}")
    print(f"总支出: {result['grand_total']:.2f}\n")

    for c in result['category_pct']:
        print(f"  {c['category']}: {c['total']:.2f} ({c['pct']:.1f}%) [{c['count']}笔, 均{c['avg']:.1f}]")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="饼干记账 v2.0")

    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # add
    p = subparsers.add_parser('add', help='添加账单')
    p.add_argument('--category', required=True, help='分类')
    p.add_argument('--amount', required=True, type=float, help='金额（负数为支出）')
    p.add_argument('--time', default=None, help='时间 YYYY-MM-DD HH:MM:SS')
    p.add_argument('--account', default='', help='账户')
    p.add_argument('--ledger', default='生活', help='账本')
    p.add_argument('--currency', default='人民币', help='货币')
    p.add_argument('--note', default='', help='备注')

    # list
    p = subparsers.add_parser('list', help='查询记录')
    p.add_argument('--date', default=None, help='日期 YYYY-MM-DD')
    p.add_argument('--from', dest='from_date', default=None, help='开始日期 YYYY-MM-DD')
    p.add_argument('--to', dest='to_date', default=None, help='结束日期 YYYY-MM-DD')
    p.add_argument('--category', default=None, help='按分类筛选')

    # search
    p = subparsers.add_parser('search', help='搜索备注关键词')
    p.add_argument('keyword', help='关键词')

    # summary
    subparsers.add_parser('summary', help='今日摘要')

    # monthly
    p = subparsers.add_parser('monthly', help='月度汇总')
    p.add_argument('--month', required=True, help='月份 YYYY-MM')

    # compare
    p = subparsers.add_parser('compare', help='周期对比')
    p.add_argument('--period', default='week', choices=['week', 'month'], help='对比周期 (week/month)')

    # recent
    p = subparsers.add_parser('recent', help='最近N条')
    p.add_argument('--limit', type=int, default=10, help='条数')

    # breakdown
    p = subparsers.add_parser('breakdown', help='分类明细')
    p.add_argument('--from', dest='from_date', default=None, help='开始日期 YYYY-MM-DD')
    p.add_argument('--to', dest='to_date', default=None, help='结束日期 YYYY-MM-DD')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        'add': cmd_add,
        'list': cmd_list,
        'search': cmd_search,
        'summary': cmd_summary,
        'monthly': cmd_monthly,
        'compare': cmd_compare,
        'recent': cmd_recent,
        'breakdown': cmd_breakdown,
    }

    cmd = commands.get(args.command)
    if cmd:
        cmd(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()