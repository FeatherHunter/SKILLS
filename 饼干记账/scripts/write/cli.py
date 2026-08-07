#!/usr/bin/env python3
"""饼干记账 · 写入域 CLI(记支出/记收入/拍账单/改记录/批量录入/撤销/报销)

用法:
    python3 scripts/write/cli.py add --category 餐饮/外卖/午餐 --amount -35.0 --note "午饭"
    python3 scripts/write/cli.py update --id 123 --amount -38.0
"""

import sys
import json
from datetime import datetime
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from db import add_bill, get_by_id, update_bill
from validators import (
    ValidationError, validate_amount, validate_category, validate_time,
    validate_record, DEFAULTS as VALIDATOR_DEFAULTS,
)
from cli_utils import reconfigure_utf8, format_validation_error, emit_ok, emit_error

reconfigure_utf8()


def cmd_add(args):
    """添加账单"""
    time_str = args.time or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        record = validate_record({
            "category": args.category,
            "amount": args.amount,
            "time": time_str,
            "account": args.account or VALIDATOR_DEFAULTS["account"],
            "ledger": args.ledger or VALIDATOR_DEFAULTS["ledger"],
            "currency": args.currency or VALIDATOR_DEFAULTS["currency"],
            "note": args.note or VALIDATOR_DEFAULTS["note"],
        })
    except ValidationError as e:
        format_validation_error(e, json_mode=getattr(args, 'json', False))
        sys.exit(1)
    result = add_bill(
        category=record["category"],
        amount=record["amount"],
        time_str=record["time"],
        account=record["account"],
        ledger=record["ledger"],
        currency=record["currency"],
        note=record["note"],
    )
    print(f"✓ 已记录：{result['category']} {result['amount']:.2f}")
    return result


def cmd_update(args):
    """修改账单(按 ID)"""
    record_id = args.id
    original = get_by_id(record_id)
    if not original:
        print(f"✗ ID={record_id} 不存在")
        return

    new_fields = {
        k: v for k, v in vars(args).items()
        if k not in ('id', 'command') and v is not None
    }

    if not new_fields:
        print("✗ 没有传入任何修改字段(至少传一个: --category/--amount/--time/--account/--ledger/--currency/--note)")
        return

    try:
        if "amount" in new_fields:
            new_fields["amount"] = validate_amount(new_fields["amount"])
        if "category" in new_fields:
            new_fields["category"] = validate_category(new_fields["category"])
        if "time" in new_fields:
            new_fields["time"] = validate_time(new_fields["time"])
    except ValidationError as e:
        format_validation_error(e, json_mode=getattr(args, 'json', False))
        sys.exit(1)

    print(f"📝 当前记录(ID={record_id}):")
    print(f"   {original['time']} | {original['category']} | {original['amount']:.2f} | {original.get('note', '')}")
    print(f"\n🔧 待修改:")
    for k, v in new_fields.items():
        old_val = original.get(k, '')
        if isinstance(old_val, float):
            print(f"   {k}: {old_val:.2f}  →  {v}")
        else:
            print(f"   {k}: {old_val}  →  {v}")

    result = update_bill(record_id, **new_fields)
    if result.get("success"):
        print(f"\n✓ 已修改(ID={record_id}): {', '.join(result['updated_fields'])}")
    else:
        print(f"\n✗ 修改失败: {result.get('error', '未知错误')}")
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="饼干记账 · 写入域 v2.0")
    sub = parser.add_subparsers(dest='command', help='子命令')

    p = sub.add_parser('add', help='添加账单')
    p.add_argument('--category', required=True, help='分类')
    p.add_argument('--amount', required=True, type=float, help='金额（负数为支出）')
    p.add_argument('--time', default=None, help='时间 YYYY-MM-DD HH:MM:SS')
    p.add_argument('--account', default='', help='账户')
    p.add_argument('--ledger', default='生活', help='账本')
    p.add_argument('--currency', default='人民币', help='货币')
    p.add_argument('--note', default='', help='备注')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('update', help='修改账单（按 ID,至少传一个字段）')
    p.add_argument('--id', required=True, type=int, help='记录 ID')
    p.add_argument('--category', default=None, help='分类')
    p.add_argument('--amount', default=None, type=float, help='金额（负数为支出）')
    p.add_argument('--time', default=None, help='时间 YYYY-MM-DD HH:MM:SS')
    p.add_argument('--account', default=None, help='账户')
    p.add_argument('--ledger', default=None, help='账本')
    p.add_argument('--currency', default=None, help='货币')
    p.add_argument('--note', default=None, help='备注')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    commands = {'add': cmd_add, 'update': cmd_update}
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
