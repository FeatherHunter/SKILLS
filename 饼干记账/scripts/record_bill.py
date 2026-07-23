#!/usr/bin/env python3
"""
饼干记账 CLI v2.2

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
    python3 record_bill.py breakdown --from 2026-05-01 --to 2026-05-31
    python3 record_bill.py overview --month 2026-05
    python3 record_bill.py stats
"""

import sys
import json
from datetime import datetime
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent.resolve()
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from db import (
    add_bill,
    list_today, list_date, list_date_range,
    list_by_category, search_keyword, list_recent,
    get_by_id, update_bill
)
from analyze import (
    get_today_summary, monthly_summary,
    compare_periods, get_category_breakdown
)


def _format_record(r: dict) -> str:
    """格式化单条记录"""
    time = r.get('time', 'N/A')
    category = r.get('category', 'N/A')
    amount = r.get('amount', 0)
    note = r.get('note', '')
    return f"{time} | {category} | {amount:.2f} | {note}"


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


def cmd_update(args):
    """修改账单(按 ID)"""
    record_id = args.id

    # 先查原记录,展示给用户
    original = get_by_id(record_id)
    if not original:
        print(f"✗ ID={record_id} 不存在")
        return

    # 收集待更新字段(白名单已由 update_bill 过滤,这里只筛 None)
    new_fields = {
        k: v for k, v in vars(args).items()
        if k not in ('id', 'command') and v is not None
    }

    if not new_fields:
        print("✗ 没有传入任何修改字段(至少传一个: --category/--amount/--time/--account/--ledger/--currency/--note)")
        return

    # 展示 diff
    print(f"📝 当前记录(ID={record_id}):")
    print(f"   {original['time']} | {original['category']} | {original['amount']:.2f} | {original.get('note', '')}")
    print(f"\n🔧 待修改:")
    for k, v in new_fields.items():
        old_val = original.get(k, '')
        if isinstance(old_val, float):
            print(f"   {k}: {old_val:.2f}  →  {v}")
        else:
            print(f"   {k}: {old_val}  →  {v}")

    # 执行更新(diff + 确认由 AI 层负责,CLI 层按指令直接落库)
    result = update_bill(record_id, **new_fields)

    if result.get("success"):
        print(f"\n✓ 已修改(ID={record_id}): {', '.join(result['updated_fields'])}")
    else:
        print(f"\n✗ 修改失败: {result.get('error', '未知错误')}")
    return result


def cmd_list(args):
    """查询记录"""
    records = []
    filter_desc = {}

    if args.date:
        records = list_date(args.date)
        filter_desc = {"date": args.date}
    elif args.from_date and args.to_date:
        records = list_date_range(args.from_date, args.to_date)
        filter_desc = {"from": args.from_date, "to": args.to_date}
    elif args.from_date or args.to_date:
        if getattr(args, 'json', False):
            print(json.dumps({"status": "error", "data": None, "message": "--from 和 --to 必须同时指定"}, ensure_ascii=False, indent=2))
        else:
            print("错误：--from 和 --to 必须同时指定")
        return
    elif args.category:
        records = list_by_category(args.category)
        filter_desc = {"category": args.category}
    else:
        records = list_today()
        filter_desc = {"date": "today"}

    if getattr(args, 'json', False):
        print(json.dumps({
            "status": "ok",
            "data": {"filter": filter_desc, "count": len(records), "records": records},
            "message": f"查询结果 {len(records)} 条"
        }, ensure_ascii=False, indent=2))
        return records

    if not records:
        print("(无记录)")
        return

    for r in records:
        print(_format_record(r))
    return records


def cmd_search(args):
    """搜索备注关键词"""
    records = search_keyword(args.keyword)
    if getattr(args, 'json', False):
        print(json.dumps({
            "status": "ok",
            "data": {"keyword": args.keyword, "count": len(records), "records": records},
            "message": f"搜索结果: {args.keyword}"
        }, ensure_ascii=False, indent=2))
        return records
    if not records:
        print(f"(无匹配 '{args.keyword}' 的记录)")
        return
    print(f"=== 搜索结果: '{args.keyword}' ({len(records)}条) ===")
    for r in records:
        print(_format_record(r))
    return records


def cmd_summary(args):
    """今日摘要"""
    result = get_today_summary()
    if getattr(args, 'json', False):
        print(json.dumps({
            "status": "ok",
            "data": result,
            "message": "今日摘要"
        }, ensure_ascii=False, indent=2))
        return result
    print(f"今日 {result.get('date', 'N/A')}")
    print(f"记录数: {result.get('count', 0)}")
    print(f"支出: {result.get('expense', 0):.2f}")
    print(f"收入: {result.get('income', 0):.2f}")
    print(f"净额: {result.get('net', 0):.2f}")
    return result


def cmd_monthly(args):
    """月度汇总"""
    result = monthly_summary(args.month)
    if getattr(args, 'json', False):
        print(json.dumps({
            "status": "ok",
            "data": result,
            "message": f"{args.month} 月度汇总"
        }, ensure_ascii=False, indent=2))
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
        if getattr(args, 'json', False):
            print(json.dumps({"status": "error", "data": None, "message": result["error"]}, ensure_ascii=False, indent=2))
        else:
            print(result["error"])
        return

    if getattr(args, 'json', False):
        print(json.dumps({
            "status": "ok",
            "data": result,
            "message": f"{'周' if period == 'week' else '月'}度对比"
        }, ensure_ascii=False, indent=2))
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


def cmd_recent(args):
    """最近N条"""
    limit = args.limit or 10
    records = list_recent(limit)
    if getattr(args, 'json', False):
        print(json.dumps({
            "status": "ok",
            "data": {"count": len(records), "limit": limit, "records": records},
            "message": f"最近 {len(records)} 条"
        }, ensure_ascii=False, indent=2))
        return records
    if not records:
        print("(无记录)")
        return
    print(f"=== 最近 {len(records)} 条 ===")
    for r in records:
        print(_format_record(r))
    return records


def cmd_breakdown(args):
    """分类明细"""
    from_date = args.from_date
    to_date = args.to_date
    result = get_category_breakdown(from_date, to_date)

    if getattr(args, 'json', False):
        print(json.dumps({
            "status": "ok",
            "data": result,
            "message": "分类支出明细"
        }, ensure_ascii=False, indent=2))
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
    import sqlite3
    from db import init_db, TABLE_NAME
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
            print(json.dumps({
                "status": "ok",
                "data": data,
                "message": f"{month} 收支总览"
            }, ensure_ascii=False, indent=2))
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
    import sqlite3
    from db import init_db, TABLE_NAME
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
            print(json.dumps({
                "status": "ok",
                "data": data,
                "message": "记账统计"
            }, ensure_ascii=False, indent=2))
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
    parser = argparse.ArgumentParser(description="饼干记账 v2.2")

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

    # update
    p = subparsers.add_parser('update', help='修改账单（按 ID,至少传一个字段）')
    p.add_argument('--id', required=True, type=int, help='记录 ID')
    p.add_argument('--category', default=None, help='分类')
    p.add_argument('--amount', default=None, type=float, help='金额（负数为支出）')
    p.add_argument('--time', default=None, help='时间 YYYY-MM-DD HH:MM:SS')
    p.add_argument('--account', default=None, help='账户')
    p.add_argument('--ledger', default=None, help='账本')
    p.add_argument('--currency', default=None, help='货币')
    p.add_argument('--note', default=None, help='备注')

    # list
    p = subparsers.add_parser('list', help='查询记录')
    p.add_argument('--date', default=None, help='日期 YYYY-MM-DD')
    p.add_argument('--from', dest='from_date', default=None, help='开始日期 YYYY-MM-DD')
    p.add_argument('--to', dest='to_date', default=None, help='结束日期 YYYY-MM-DD')
    p.add_argument('--category', default=None, help='按分类筛选')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式（{status,data,message}）')

    # search
    p = subparsers.add_parser('search', help='搜索备注关键词')
    p.add_argument('keyword', help='关键词')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    # summary
    p = subparsers.add_parser('summary', help='今日摘要')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    # monthly
    p = subparsers.add_parser('monthly', help='月度汇总')
    p.add_argument('--month', required=True, help='月份 YYYY-MM')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    # compare
    p = subparsers.add_parser('compare', help='周期对比')
    p.add_argument('--period', default='week', choices=['week', 'month'], help='对比周期 (week/month)')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    # recent
    p = subparsers.add_parser('recent', help='最近N条')
    p.add_argument('--limit', type=int, default=10, help='条数')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    # breakdown
    p = subparsers.add_parser('breakdown', help='分类明细')
    p.add_argument('--from', dest='from_date', default=None, help='开始日期 YYYY-MM-DD')
    p.add_argument('--to', dest='to_date', default=None, help='结束日期 YYYY-MM-DD')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    # overview
    p = subparsers.add_parser('overview', help='收支总览')
    p.add_argument('--month', default=None, help='月份 YYYY-MM（默认当月）')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    # stats
    p = subparsers.add_parser('stats', help='记账统计')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        'add': cmd_add,
        'update': cmd_update,
        'list': cmd_list,
        'search': cmd_search,
        'summary': cmd_summary,
        'monthly': cmd_monthly,
        'compare': cmd_compare,
        'recent': cmd_recent,
        'breakdown': cmd_breakdown,
        'overview': cmd_overview,
        'stats': cmd_stats,
    }

    cmd = commands.get(args.command)
    if cmd:
        try:
            cmd(args)
        except ValueError as e:
            if getattr(args, 'json', False):
                print(json.dumps({"status": "error", "data": None, "message": f"参数错误：{e}"}, ensure_ascii=False))
            else:
                print(f"参数错误：{e}")
        except FileNotFoundError as e:
            if getattr(args, 'json', False):
                print(json.dumps({"status": "error", "data": None, "message": f"文件未找到：{e}"}, ensure_ascii=False))
            else:
                print(f"文件未找到：{e}")
        except PermissionError as e:
            if getattr(args, 'json', False):
                print(json.dumps({"status": "error", "data": None, "message": f"权限不足：{e}"}, ensure_ascii=False))
            else:
                print(f"权限不足：{e}")
        except Exception as e:
            if getattr(args, 'json', False):
                print(json.dumps({"status": "error", "data": None, "message": f"执行出错：{e}"}, ensure_ascii=False))
            else:
                print(f"执行出错：{e}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
