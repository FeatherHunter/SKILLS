#!/usr/bin/env python3
"""饼干记账 · 分析域 CLI(看月度/看对比/看分类/看总览/做统计/日历/目标/周期洞察)

用法:
    python3 scripts/analysis/cli.py monthly --month 2026-05
    python3 scripts/analysis/cli.py compare --period week
    python3 scripts/analysis/cli.py breakdown --from 2026-05-01 --to 2026-05-31
    python3 scripts/analysis/cli.py overview --month 2026-05
    python3 scripts/analysis/cli.py stats
"""

import sys
import sqlite3
from datetime import datetime
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from analyze import monthly_summary, compare_periods, get_category_breakdown
from db import init_db, TABLE_NAME
from cli_utils import reconfigure_utf8, emit_ok, emit_error

reconfigure_utf8()


def cmd_monthly(args):
    """月度汇总"""
    result = monthly_summary(args.month)
    if getattr(args, 'json', False):
        emit_ok(result, f"{args.month} 月度汇总")
        return result
    print(f"=== {args.month} 月度汇总 ===")
    print(f"支出: {result.get('expense', 0):.2f}")
    print(f"收入: {result.get('income', 0):.2f}")
    print(f"净额: {result.get('net', 0):.2f}")
    categories = result.get('categories', [])
    if categories:
        print("\n分类明细:")
        for c in categories:
            print(f"  {c.get('category', 'N/A')}: {c.get('total', 0):.2f} ({c.get('count', 0)}笔)")
    return result


def cmd_compare(args):
    """周期对比"""
    period = args.period or "week"
    result = compare_periods(period)

    if "error" in result:
        emit_error(result["error"]) if getattr(args, 'json', False) else print(result["error"])
        return

    if getattr(args, 'json', False):
        emit_ok(result, f"{'周' if period == 'week' else '月'}度对比")
        return result

    label = "周" if period == "week" else "月"
    print(f"=== {label}度对比 ===\n")
    this = result.get('this', {})
    last = result.get('last', {})
    print(f"{this.get('label', 'N/A')}")
    print(f"  支出: {this.get('expense', 0):.2f}")
    print(f"  收入: {this.get('income', 0):.2f}")
    print(f"  净额: {this.get('net', 0):.2f}")
    print(f"\n{last.get('label', 'N/A')}")
    print(f"  支出: {last.get('expense', 0):.2f}")
    print(f"  收入: {last.get('income', 0):.2f}")
    print(f"  净额: {last.get('net', 0):.2f}")
    print(f"\n变化:")
    change = result.get('change', {})
    diff = change.get('expense_diff', 0)
    pct = change.get('expense_pct', 0)
    direction = "↑" if diff > 0 else "↓" if diff < 0 else "→"
    print(f"  支出 {direction} {abs(diff):.2f} ({abs(pct):.1f}%)")
    return result


def cmd_breakdown(args):
    """分类明细"""
    from_date = args.from_date
    to_date = args.to_date
    result = get_category_breakdown(from_date, to_date)

    if getattr(args, 'json', False):
        emit_ok(result, "分类支出明细")
        return result

    print(f"=== 分类支出明细 ===")
    if from_date or to_date:
        print(f"期间: {result.get('from', 'N/A')} ~ {result.get('to', 'N/A')}")
    print(f"总支出: {result.get('grand_total', 0):.2f}\n")

    for c in result.get('category_pct', []):
        print(f"  {c.get('category', 'N/A')}: {c.get('total', 0):.2f} ({c.get('pct', 0):.1f}%) [{c.get('count', 0)}笔, 均{c.get('avg', 0):.1f}]")
    return result


def cmd_overview(args):
    """收支总览"""
    month = args.month or datetime.now().strftime("%Y-%m")
    year_int = int(month.split("-")[0])
    month_int = int(month.split("-")[1])
    if month_int == 12:
        next_month_str = f"{year_int + 1}-01-01"
    else:
        next_month_str = f"{year_int}-{month_int + 1:02d}-01"
    start_str = f"{month}-01 00:00:00"
    next_month_start = f"{next_month_str} 00:00:00"
    conn = init_db()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT
                COUNT(*) as count,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expense,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
                SUM(amount) as net
            FROM {TABLE_NAME}
            WHERE time >= ? AND time < ?
        """, (start_str, next_month_start))
        row = cursor.fetchone()
        data = {
            "month": month,
            "count": row['count'] or 0,
            "expense": row['expense'] or 0,
            "income": row['income'] or 0,
            "net": row['net'] or 0
        }
        if getattr(args, 'json', False):
            emit_ok(data, f"{month} 收支总览")
            return data
        print(f"=== {month} 收支总览 ===")
        print(f"笔数: {data['count']}")
        print(f"支出: {data['expense']:.2f}")
        print(f"收入: {data['income']:.2f}")
        print(f"净额: {data['net']:.2f}")
        return data
    finally:
        conn.close()


def cmd_stats(args):
    """记账统计"""
    conn = init_db()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT
                COUNT(*) as total_records,
                COUNT(DISTINCT SUBSTR(time, 1, 10)) as total_days,
                MIN(time) as first_record,
                MAX(time) as last_record
            FROM {TABLE_NAME}
        """)
        row = cursor.fetchone()
        data = {
            "total_records": row['total_records'],
            "total_days": row['total_days'],
            "first_record": row['first_record'] or None,
            "last_record": row['last_record'] or None
        }
        if getattr(args, 'json', False):
            emit_ok(data, "记账统计")
            return data
        print("=== 记账统计 ===")
        print(f"总笔数: {data['total_records']}")
        print(f"记账天数: {data['total_days']}")
        print(f"首笔时间: {data['first_record'] or 'N/A'}")
        print(f"最近记录: {data['last_record'] or 'N/A'}")
        return data
    finally:
        conn.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="饼干记账 · 分析域 v2.0")
    sub = parser.add_subparsers(dest='command', help='子命令')

    p = sub.add_parser('monthly', help='月度汇总')
    p.add_argument('--month', required=True, help='月份 YYYY-MM')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('compare', help='周期对比')
    p.add_argument('--period', default='week', choices=['week', 'month'], help='对比周期 (week/month)')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('breakdown', help='分类明细')
    p.add_argument('--from', dest='from_date', default=None, help='开始日期 YYYY-MM-DD')
    p.add_argument('--to', dest='to_date', default=None, help='结束日期 YYYY-MM-DD')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('overview', help='收支总览')
    p.add_argument('--month', default=None, help='月份 YYYY-MM（默认当月）')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('stats', help='记账统计')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    commands = {'monthly': cmd_monthly, 'compare': cmd_compare, 'breakdown': cmd_breakdown, 'overview': cmd_overview, 'stats': cmd_stats}
    cmd = commands.get(args.command)
    if cmd:
        try:
            cmd(args)
        except ValueError as e:
            emit_error(f"参数错误：{e}") if getattr(args, 'json', False) else print(f"参数错误：{e}")
        except Exception as e:
            emit_error(f"执行出错：{e}") if getattr(args, 'json', False) else print(f"执行出错：{e}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
