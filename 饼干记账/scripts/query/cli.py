#!/usr/bin/env python3
"""饼干记账 · 查询域 CLI(查今天/查日期/查范围/查分类/查最近/搜备注/查标签/账户总览/对账)

用法:
    python3 scripts/query/cli.py list --date 2026-05-01
    python3 scripts/query/cli.py search "午饭"
    python3 scripts/query/cli.py recent --limit 10
    python3 scripts/query/cli.py summary
"""

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from db import (
    list_today, list_date, list_date_range,
    list_by_category, search_keyword, list_recent,
)
from analyze import get_today_summary
from cli_utils import reconfigure_utf8, format_record, emit_ok, emit_error

reconfigure_utf8()


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
        emit_error("--from 和 --to 必须同时指定") if getattr(args, 'json', False) else print("错误：--from 和 --to 必须同时指定")
        return
    elif args.category:
        records = list_by_category(args.category)
        filter_desc = {"category": args.category}
    else:
        records = list_today()
        filter_desc = {"date": "today"}

    if getattr(args, 'json', False):
        emit_ok({"filter": filter_desc, "count": len(records), "records": records}, f"查询结果 {len(records)} 条")
        return records

    if not records:
        print("(无记录)")
        return
    for r in records:
        print(format_record(r))
    return records


def cmd_search(args):
    """搜索备注关键词"""
    records = search_keyword(args.keyword)
    if getattr(args, 'json', False):
        emit_ok({"keyword": args.keyword, "count": len(records), "records": records}, f"搜索结果: {args.keyword}")
        return records
    if not records:
        print(f"(无匹配 '{args.keyword}' 的记录)")
        return
    print(f"=== 搜索结果: '{args.keyword}' ({len(records)}条) ===")
    for r in records:
        print(format_record(r))
    return records


def cmd_recent(args):
    """最近N条"""
    limit = args.limit or 10
    records = list_recent(limit)
    if getattr(args, 'json', False):
        emit_ok({"count": len(records), "limit": limit, "records": records}, f"最近 {len(records)} 条")
        return records
    if not records:
        print("(无记录)")
        return
    print(f"=== 最近 {len(records)} 条 ===")
    for r in records:
        print(format_record(r))
    return records


def cmd_summary(args):
    """今日摘要"""
    result = get_today_summary()
    if getattr(args, 'json', False):
        emit_ok(result, "今日摘要")
        return result
    print(f"今日 {result.get('date', 'N/A')}")
    print(f"记录数: {result.get('count', 0)}")
    print(f"支出: {result.get('expense', 0):.2f}")
    print(f"收入: {result.get('income', 0):.2f}")
    print(f"净额: {result.get('net', 0):.2f}")
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="饼干记账 · 查询域 v2.0")
    sub = parser.add_subparsers(dest='command', help='子命令')

    p = sub.add_parser('list', help='查询记录')
    p.add_argument('--date', default=None, help='日期 YYYY-MM-DD')
    p.add_argument('--from', dest='from_date', default=None, help='开始日期 YYYY-MM-DD')
    p.add_argument('--to', dest='to_date', default=None, help='结束日期 YYYY-MM-DD')
    p.add_argument('--category', default=None, help='按分类筛选')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('search', help='搜索备注关键词')
    p.add_argument('keyword', help='关键词')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('recent', help='最近N条')
    p.add_argument('--limit', type=int, default=10, help='条数')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('summary', help='今日摘要')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    commands = {'list': cmd_list, 'search': cmd_search, 'recent': cmd_recent, 'summary': cmd_summary}
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
