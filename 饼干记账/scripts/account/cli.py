#!/usr/bin/env python3
"""饼干记账 · 账户域 CLI(4 场景 · 直达式 · scenes/account.yaml)

场景 → 子命令:
    新增账户    → add --name X [--type Y](账户表 = goals.json accounts)
    改账户      → update --name X [--new-name Y | --disable | --enable](改名 / 停用 / 启用)
    账户转账    → transfer --amount X --from A --to B [--time T](两笔 #转账,不影响收支统计)
    看账户汇总  → summary(各账户余额卡 = 收支累计推算 + 最近流水;停用灰显)

载体(G2/G1 定案):
    账户清单 = $DATA_DIR/goals.json 顶层 "accounts" 键(目标域键隔离 · 原子写保留其他键)
    账户流水 = bills.account 字段(无独立账户表);余额 = 收入 − 支出 累计推算
    转账     = 两笔记录:转出支出(账户 A)+ 转入收入(账户 B)
                分类 = 转账/转出 | 转账/转入,账本 = 转账,备注 = #转账(转出/转入方向)
                账户域收支统计按「转账」分类排除(不影响收支统计),余额计算含转账(两账户正确增减)

用法:
    python3 scripts/account/cli.py add --name 招行卡 --type 银行卡
    python3 scripts/account/cli.py list
    python3 scripts/account/cli.py update --name 招行卡 --new-name 招行工资卡
    python3 scripts/account/cli.py update --name 招行卡 --disable
    python3 scripts/account/cli.py update --name 招行卡 --enable
    python3 scripts/account/cli.py transfer --amount 500 --from 支付宝 --to 招行卡
    python3 scripts/account/cli.py summary
"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from db import _find_db_path, DB_FILENAME, insert_record
from cli_utils import reconfigure_utf8, emit_ok, emit_error

reconfigure_utf8()

GOALS_FILENAME = "goals.json"

# 转账分类(不入 validators 白名单 · 公共层零改动 · 隔离契约内自包含)
TRANSFER_OUT_CATEGORY = "转账/转出"
TRANSFER_IN_CATEGORY = "转账/转入"
TRANSFER_LEDGER = "转账"


# ── goals.json 读写(账户表 · 顶层 "accounts" 键,与目标域键隔离)────────────────

def _goals_path() -> Path:
    return _find_db_path(_SCRIPTS.parent, DB_FILENAME).parent / GOALS_FILENAME


def _load_goals() -> dict:
    p = _goals_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise RuntimeError(f"goals.json 读取失败(可能被其他域写入中): {e}")


def _save_goals(data: dict) -> None:
    """原子写:先写 .tmp 再 replace(防并发半写)"""
    p = _goals_path()
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def _accounts() -> list:
    """账户表(accounts 键)"""
    return _load_goals().get("accounts", [])


def _save_accounts(accounts: list) -> None:
    data = _load_goals()
    data["accounts"] = accounts
    _save_goals(data)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── 新增账户 ─────────────────────────────────────────────────────────────────

def cmd_add(args):
    name = (args.name or "").strip()
    if not name:
        raise ValueError("账户名不能为空(新增账户需要 --name)")
    if len(name) > 30:
        raise ValueError(f"账户名过长({len(name)} 字,最多 30 字)")
    for a in _accounts():
        if a["name"] == name:
            raise ValueError(f"账户「{name}」已存在(重复新增需用户确认)")
    acct = {
        "name": name,
        "type": (args.type or "").strip(),
        "disabled": False,
        "created_at": _now(),
    }
    accounts = _accounts()
    accounts.append(acct)
    _save_accounts(accounts)
    data = {"account": acct, "count": len(accounts)}
    if getattr(args, 'json', False):
        emit_ok(data, f"已新增账户 {name}")
        return data
    print(f"✓ 已新增账户 {name}(类型 {acct['type'] or '未填'})")
    return data


# ── 账户清单(AI 定位候选 / 表单下拉数据源)────────────────────────────────────

def cmd_list(args):
    accounts = _accounts()
    data = {"count": len(accounts), "accounts": accounts}
    if getattr(args, 'json', False):
        emit_ok(data, f"账户清单 {len(accounts)} 个")
        return data
    if not accounts:
        print("(账户表为空 · 先使用「新增账户」)")
        return data
    for a in accounts:
        flag = " · 已停用" if a.get("disabled") else ""
        print(f"  {a['name']}({a.get('type') or '未填类型'}){flag}")
    return data


# ── 修改账户(改名 / 停用 / 启用)──────────────────────────────────────────────

def _find_account(accounts: list, name: str):
    for a in accounts:
        if a["name"] == name:
            return a
    return None


def cmd_update(args):
    name = (args.name or "").strip()
    if not name:
        raise ValueError("目标账户不能为空(改账户需要 --name)")
    accounts = _accounts()
    target = _find_account(accounts, name)
    if target is None:
        raise ValueError(f"账户「{name}」不存在(可先用 account list 查看账户表)")

    changes = []
    if args.new_name:
        new_name = (args.new_name or "").strip()
        if not new_name:
            raise ValueError("新账户名不能为空")
        if len(new_name) > 30:
            raise ValueError(f"新账户名过长({len(new_name)} 字,最多 30 字)")
        if new_name == name:
            raise ValueError("新账户名与原名相同,无需修改")
        if _find_account(accounts, new_name) is not None:
            raise ValueError(f"账户「{new_name}」已存在,不能改名为重名")
        # 账户表改名
        target["name"] = new_name
        changes.append(f"改名:{name} → {new_name}")
        # 历史记录保留(逐条改名,bills.account 跟随;含软删记录,恢复后名称一致)
        from db import init_db, TABLE_NAME
        conn = init_db()
        try:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE {TABLE_NAME} SET account = ? WHERE account = ?",
                (new_name, name),
            )
            conn.commit()
            renamed_rows = cur.rowcount
        finally:
            conn.close()
        changes.append(f"历史流水改名 {renamed_rows} 笔")
    if args.disable:
        target["disabled"] = True
        changes.append("停用(历史记录保留,汇总灰显)")
    if args.enable:
        target["disabled"] = False
        changes.append("启用(恢复参与汇总)")
    if not changes:
        raise ValueError("没有可执行的变更(至少传 --new-name / --disable / --enable 之一)")
    _save_accounts(accounts)
    data = {"account": target, "changes": changes}
    if getattr(args, 'json', False):
        emit_ok(data, f"已更新账户 {name}")
        return data
    for c in changes:
        print(f"✓ {c}")
    return data


# ── 账户转账(两笔 #转账 · 不影响收支统计)──────────────────────────────────────

def cmd_transfer(args):
    from validators import validate_amount, validate_time
    amount = validate_amount(args.amount)
    from_acct = (args.from_acct or "").strip()
    to_acct = (args.to_acct or "").strip()
    if not from_acct:
        raise ValueError("转出账户不能为空(--from)")
    if not to_acct:
        raise ValueError("转入账户不能为空(--to)")
    if from_acct == to_acct:
        raise ValueError("转出与转入账户相同,无法转账")
    if amount < 0:
        raise ValueError("转账金额应为正数(账户间移动不分收支方向)")

    time_str = args.time or _now()
    validate_time(time_str)  # 复用白名单校验器(时间格式契约)

    # 两笔记录(同一时刻同一笔转账):A 转出支出 + B 转入收入
    out_note = f"#转账 转出至{to_acct}"
    in_note = f"#转账 转入自{from_acct}"
    r1 = insert_record(TRANSFER_OUT_CATEGORY, -amount, time_str,
                       account=from_acct, ledger=TRANSFER_LEDGER, note=out_note)
    r2 = insert_record(TRANSFER_IN_CATEGORY, amount, time_str,
                       account=to_acct, ledger=TRANSFER_LEDGER, note=in_note)
    data = {
        "amount": round(amount, 2), "from": from_acct, "to": to_acct,
        "time": time_str,
        "out_record": r1, "in_record": r2,
        "note": f"#转账({from_acct} → {to_acct} {round(amount, 2):.2f})",
    }
    if getattr(args, 'json', False):
        emit_ok(data, f"已转账 {from_acct} → {to_acct} {amount:.2f}")
        return data
    print(f"✓ 已转账 {from_acct} → {to_acct} {amount:.2f}")
    print(f"  {from_acct} 转出: {TRANSFER_OUT_CATEGORY} -{amount:.2f}({out_note})")
    print(f"  {to_acct} 转入: {TRANSFER_IN_CATEGORY} +{amount:.2f}({in_note})")
    return data


# ── 看账户汇总(余额卡 = 收支累计推算 · 停用灰显)────────────────────────────────

def _is_transfer(record) -> bool:
    return str(record.get("category") or "").startswith("转账/")


def cmd_summary(args):
    from db import fetch_all
    records = fetch_all()  # 排除软删
    registered = _accounts()
    registered_names = {a["name"] for a in registered}
    disabled_names = {a["name"] for a in registered if a.get("disabled")}

    # 账户全集 = 账户表(保持登记顺序)+ bills 独有账户(未登记,自动暴露)
    names: list = []
    seen = set()
    for a in registered:
        names.append(a["name"])
        seen.add(a["name"])
    bills_only = sorted({str(r.get("account") or "").strip() for r in records if (r.get("account") or "").strip()})
    for n in bills_only:
        if n not in seen:
            names.append(n)
            seen.add(n)

    cards = []
    totals = {"income": 0.0, "expense": 0.0, "transfer_in": 0.0, "transfer_out": 0.0,
              "balance": 0.0, "count": 0}
    for n in names:
        rs = [r for r in records if str(r.get("account") or "") == n]
        income = round(sum(r["amount"] for r in rs if r.get("amount", 0) > 0 and not _is_transfer(r)), 2)
        expense = round(sum(abs(r["amount"]) for r in rs if r.get("amount", 0) < 0 and not _is_transfer(r)), 2)
        tin = round(sum(r["amount"] for r in rs if r.get("amount", 0) > 0 and _is_transfer(r)), 2)
        tout = round(sum(abs(r["amount"]) for r in rs if r.get("amount", 0) < 0 and _is_transfer(r)), 2)
        balance = round(income - expense + tin - tout, 2)
        last_time = max((str(r.get("time") or "") for r in rs), default="")
        meta = _find_account(registered, n)
        card = {
            "name": n,
            "type": (meta.get("type") if meta else "") or "",
            "disabled": n in disabled_names,
            "registered": meta is not None,
            "income": income, "expense": expense,
            "transfer_in": tin, "transfer_out": tout,
            "balance": balance, "count": len(rs), "last_time": last_time,
        }
        cards.append(card)
        if not card["disabled"]:
            totals["income"] += income
            totals["expense"] += expense
            totals["transfer_in"] += tin
            totals["transfer_out"] += tout
            totals["balance"] += balance
            totals["count"] += len(rs)

    for k in totals:
        totals[k] = round(totals[k], 2)
    totals["net"] = round(totals["income"] - totals["expense"], 2)
    totals["transfer_count"] = sum(1 for r in records if _is_transfer(r))
    totals["transfer_total"] = round(sum(abs(r["amount"]) for r in records if _is_transfer(r)), 2)

    # 最近流水摘要(全账户最近 12 笔)
    recent = sorted(records, key=lambda r: r.get("time") or "", reverse=True)[:12]
    flows = [{
        "id": r["id"], "time": str(r.get("time") or ""),
        "category": r.get("category") or "", "amount": r.get("amount") or 0,
        "account": r.get("account") or "", "note": r.get("note") or "",
    } for r in recent]

    data = {
        "accounts": cards,
        "totals": totals,
        "flows": flows,
        "flow_count": len(flows),
    }
    if getattr(args, 'json', False):
        emit_ok(data, f"账户汇总 {len(cards)} 个账户")
        return data
    print(f"=== 账户汇总(活跃 {totals['count']} 笔 · 转账 {totals['transfer_count']} 笔) ===")
    for c in cards:
        flag = " [已停用]" if c["disabled"] else (" [未登记]" if not c["registered"] else "")
        print(f"  {c['name']}{flag}: 余额 {c['balance']:.2f}(收入 {c['income']:.2f} / 支出 {c['expense']:.2f}"
              f" / 转入 {c['transfer_in']:.2f} / 转出 {c['transfer_out']:.2f})")
    print(f"合计: 余额 {totals['balance']:.2f} · 收入 {totals['income']:.2f} · 支出 {totals['expense']:.2f} · 净额 {totals['net']:.2f}")
    return data


# ── 入口 ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="饼干记账 · 账户域 v2.0(4 场景)")
    sub = parser.add_subparsers(dest='command', help='子命令')

    p = sub.add_parser('add', help='新增账户(写入 goals.json 账户表)')
    p.add_argument('--name', required=True, help='账户名(如:招行卡 / 花呗)')
    p.add_argument('--type', default=None, help='类型(选填,如:银行卡 / 支付 / 信用)')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('list', help='账户清单')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('update', help='修改账户(改名 / 停用 / 启用)')
    p.add_argument('--name', required=True, help='目标账户名')
    p.add_argument('--new-name', default=None, help='新账户名(改名)')
    p.add_argument('--disable', action='store_true', help='停用账户(历史记录保留)')
    p.add_argument('--enable', action='store_true', help='启用账户')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('transfer', help='账户间转账(两笔 #转账,不影响收支统计)')
    p.add_argument('--amount', type=float, required=True, help='金额(正数)')
    p.add_argument('--from', dest='from_acct', required=True, help='转出账户')
    p.add_argument('--to', dest='to_acct', required=True, help='转入账户')
    p.add_argument('--time', default=None, help='时间 YYYY-MM-DD HH:MM:SS(默认现在)')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('summary', help='看账户汇总(余额卡 = 收支累计推算 · 停用灰显)')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    commands = {'add': cmd_add, 'list': cmd_list, 'update': cmd_update,
                'transfer': cmd_transfer, 'summary': cmd_summary}
    cmd = commands.get(args.command)
    if cmd:
        try:
            cmd(args)
        except (ValueError, RuntimeError) as e:
            emit_error(f"参数错误：{e}") if getattr(args, 'json', False) else print(f"✗ 参数错误：{e}")
        except Exception as e:
            emit_error(f"执行出错：{e}") if getattr(args, 'json', False) else print(f"✗ 执行出错：{e}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
